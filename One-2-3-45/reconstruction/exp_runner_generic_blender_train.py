import torch
from torch.utils.data import DataLoader
import argparse
import os
import logging
import numpy as np
from shutil import copyfile
from torch.utils.tensorboard import SummaryWriter
from icecream import ic
from tqdm import tqdm
from pyhocon import ConfigFactory
from tqdm import tqdm

from models.fields import SingleVarianceNetwork

from models.featurenet import FeatureNet

from models.trainer_generic import GenericTrainer

from models.sparse_sdf_network import SparseSdfNetwork

from models.rendering_network import GeneralRenderingNetwork

from datetime import datetime

from data.One2345_train import BlenderPerView
from termcolor import colored

from datetime import datetime

class Runner:
    def __init__(self, conf_path, mode='train', is_continue=False,
                 is_restore=False, restore_lod0=False, local_rank=0, is_finetune=False):

        # Initial setting
        self.device = torch.device('cuda:%d' % local_rank)
        # self.device = torch.device('cuda')
        self.num_devices = torch.cuda.device_count()
        self.is_continue = is_continue
        self.is_restore = is_restore
        self.restore_lod0 = restore_lod0
        self.mode = mode
        self.model_list = []
        self.logger = logging.getLogger('exp_logger')

        print(colored("detected %d GPUs" % self.num_devices, "red"))

        self.conf_path = conf_path
        self.conf = ConfigFactory.parse_file(conf_path)
        self.timestamp = None
        if not self.is_continue:
            self.timestamp = '_{:%Y_%m_%d_%H_%M_%S}'.format(datetime.now())
            self.base_exp_dir = self.conf['general.base_exp_dir'] + self.timestamp 
        else:
            self.base_exp_dir = self.conf['general.base_exp_dir']
        self.conf['general.base_exp_dir'] = self.base_exp_dir
        print(colored("base_exp_dir:  " + self.base_exp_dir, 'yellow'))
        os.makedirs(self.base_exp_dir, exist_ok=True)
        self.iter_step = 0
        self.val_step = 0

        # trainning parameters
        self.end_iter = self.conf.get_int('train.end_iter')
        self.save_freq = self.conf.get_int('train.save_freq')
        self.report_freq = self.conf.get_int('train.report_freq')
        self.val_freq = self.conf.get_int('train.val_freq')
        self.val_mesh_freq = self.conf.get_int('train.val_mesh_freq')
        self.batch_size = self.num_devices  # use DataParallel to warp
        self.validate_resolution_level = self.conf.get_int('train.validate_resolution_level')
        self.learning_rate = self.conf.get_float('train.learning_rate')
        self.learning_rate_milestone = self.conf.get_list('train.learning_rate_milestone')
        self.learning_rate_factor = self.conf.get_float('train.learning_rate_factor')
        self.use_white_bkgd = self.conf.get_bool('train.use_white_bkgd')
        self.N_rays = self.conf.get_int('train.N_rays')

        # warmup params for sdf gradient
        self.anneal_start_lod0 = self.conf.get_float('train.anneal_start', default=0)
        self.anneal_end_lod0 = self.conf.get_float('train.anneal_end', default=0)
        self.anneal_start_lod1 = self.conf.get_float('train.anneal_start_lod1', default=0)
        self.anneal_end_lod1 = self.conf.get_float('train.anneal_end_lod1', default=0)

        self.writer = None

        # Networks
        self.num_lods = self.conf.get_int('model.num_lods')

        self.rendering_network_outside = None
        self.sdf_network_lod0 = None
        self.sdf_network_lod1 = None
        self.variance_network_lod0 = None
        self.variance_network_lod1 = None
        self.rendering_network_lod0 = None
        self.rendering_network_lod1 = None
        self.pyramid_feature_network = None  # extract 2d pyramid feature maps from images, used for geometry
        self.pyramid_feature_network_lod1 = None  # may use different feature network for different lod

        # * pyramid_feature_network
        self.pyramid_feature_network = FeatureNet().to(self.device)
        self.sdf_network_lod0 = SparseSdfNetwork(**self.conf['model.sdf_network_lod0']).to(self.device)
        self.variance_network_lod0 = SingleVarianceNetwork(**self.conf['model.variance_network']).to(self.device)

        if self.num_lods > 1:
            self.sdf_network_lod1 = SparseSdfNetwork(**self.conf['model.sdf_network_lod1']).to(self.device)
            self.variance_network_lod1 = SingleVarianceNetwork(**self.conf['model.variance_network']).to(self.device)

        self.rendering_network_lod0 = GeneralRenderingNetwork(**self.conf['model.rendering_network']).to(
            self.device)

        if self.num_lods > 1:
            self.pyramid_feature_network_lod1 = FeatureNet().to(self.device)
            self.rendering_network_lod1 = GeneralRenderingNetwork(
                **self.conf['model.rendering_network_lod1']).to(self.device)
        if self.mode == 'export_mesh' or self.mode == 'val':
            base_exp_dir_to_store = os.path.join(self.base_exp_dir, '{:%Y_%m_%d_%H_%M_%S}'.format(datetime.now()))
        else:
            base_exp_dir_to_store = self.base_exp_dir

        print(colored(f"Store in: {base_exp_dir_to_store}", "blue"))
        # Renderer model
        self.trainer = GenericTrainer(
            self.rendering_network_outside,
            self.pyramid_feature_network,
            self.pyramid_feature_network_lod1,
            self.sdf_network_lod0,
            self.sdf_network_lod1,
            self.variance_network_lod0,
            self.variance_network_lod1,
            self.rendering_network_lod0,
            self.rendering_network_lod1,
            **self.conf['model.trainer'],
            timestamp=self.timestamp,
            base_exp_dir=base_exp_dir_to_store,
            conf=self.conf)

        self.data_setup()  # * data setup

        self.optimizer_setup()

        # Load checkpoint
        latest_model_name = None
        if is_continue:
            model_list_raw = os.listdir(os.path.join(self.base_exp_dir, 'checkpoints'))
            model_list = []
            for model_name in model_list_raw:
                if model_name.startswith('ckpt'):
                    if model_name[-3:] == 'pth':  # and int(model_name[5:-4]) <= self.end_iter:
                        model_list.append(model_name)
            model_list.sort()
            latest_model_name = model_list[-1]

        if latest_model_name is not None:
            self.logger.info('Find checkpoint: {}'.format(latest_model_name))
            self.load_checkpoint(latest_model_name)

        if is_finetune:
            finetuneing_ckpt = "/opt/app/One-2-3-45/reconstruction/exp/lod0/checkpoints/ckpt_215000.pth"
            self.logger.info('Loading ckpt from: {}'.format(finetuneing_ckpt))
            self.load_checkpoint(finetuneing_ckpt)

        self.trainer = torch.nn.DataParallel(self.trainer).to(self.device)

        if self.mode[:5] == 'train':
            self.file_backup()

    def optimizer_setup(self):
        self.params_to_train = self.trainer.get_trainable_params()
        self.optimizer = torch.optim.Adam(self.params_to_train, lr=self.learning_rate)

    def data_setup(self):
        """
        if use ddp, use setup() not prepare_data(),
        prepare_data() only called on 1 GPU/TPU in distributed
        :return:
        """

        self.train_dataset = BlenderPerView(
            root_dir=self.conf['dataset.trainpath'],
            split=self.conf.get_string('dataset.train_split', default='train'),
            downSample=self.conf['dataset.imgScale_train'],
            N_rays=self.N_rays,
            batch_size=self.batch_size,
            clean_image=True,  # True for training
            importance_sample=self.conf.get_bool('dataset.importance_sample', default=False),
        )

        self.val_dataset = BlenderPerView(
            root_dir=self.conf['dataset.valpath'],
            split=self.conf.get_string('dataset.test_split', default='test'),
            downSample=self.conf['dataset.imgScale_test'],
            N_rays=self.N_rays,
            batch_size=self.batch_size,
            clean_image=self.conf.get_bool('dataset.mask_out_image',
                                           default=False) if self.mode != 'train' else False,
            importance_sample=self.conf.get_bool('dataset.importance_sample', default=False),
        )

        # item = self.train_dataset.__getitem__(0)
        self.train_dataloader = DataLoader(self.train_dataset,
                                           shuffle=True,
                                        #    num_workers=4 * self.batch_size,
                                           num_workers = 0,
                                           batch_size=self.batch_size,
                                           pin_memory=True,
                                           drop_last=True
                                           )
        
        self.val_dataloader = DataLoader(self.val_dataset,
                                         shuffle=False,
                                        #  num_workers=4 * self.batch_size,
                                         num_workers = 0,
                                         batch_size=self.batch_size,
                                         pin_memory=True,
                                         drop_last=False
                                         )

        self.val_dataloader_iterator = iter(self.val_dataloader)  # - should be after "reconstruct_metas_for_gru_fusion"

    def train(self):
        self.writer = SummaryWriter(log_dir=os.path.join(self.base_exp_dir, 'logs'))

        dataloader = self.train_dataloader

        epochs_needed = int(1 + self.end_iter // len(dataloader))
        self.end_iter = epochs_needed * len(dataloader) 
        self.adjust_learning_rate()
        print(colored("starting training learning rate: {:.5f}".format(self.optimizer.param_groups[0]['lr']), "yellow"))

        background_rgb = None
        if self.use_white_bkgd:
            background_rgb = 1.0

        # print("debug validate")
        # self.validate()
        # print("finish debug validate")

        for epoch_i in range(epochs_needed):

            print(colored("current epoch %d" % epoch_i, 'red'))
            dataloader = tqdm(dataloader)

            for batch in dataloader:
                batch['batch_idx'] = torch.tensor([x for x in range(self.batch_size)])  # used to get meta

                if self.iter_step > self.end_iter:
                    break

                # - warmup params
                if self.num_lods == 1:
                    alpha_inter_ratio_lod0 = self.get_alpha_inter_ratio(self.anneal_start_lod0, self.anneal_end_lod0)
                else:
                    alpha_inter_ratio_lod0 = 1.
                alpha_inter_ratio_lod1 = self.get_alpha_inter_ratio(self.anneal_start_lod1, self.anneal_end_lod1)

                losses = self.trainer(
                    batch,
                    background_rgb=background_rgb,
                    alpha_inter_ratio_lod0=alpha_inter_ratio_lod0,
                    alpha_inter_ratio_lod1=alpha_inter_ratio_lod1,
                    iter_step=self.iter_step,
                    mode='train',
                )

                loss_types = ['loss_lod0', 'loss_lod1']

                losses_lod0 = losses['losses_lod0']
                losses_lod1 = losses['losses_lod1']
                loss = 0
                for loss_type in loss_types:
                    if losses[loss_type] is not None:
                        loss = loss + losses[loss_type].mean()
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.params_to_train, 1.0)
                self.optimizer.step()
                self.iter_step += 1

                if self.iter_step % self.report_freq == 0:
                    self.writer.add_scalar('Loss/loss', loss, self.iter_step)
                    self.writer.add_scalar('Loss/loss_fg_bg_loss', losses_lod0['fg_bg_loss'].mean(), self.iter_step)
                    if losses_lod0 is not None:
                        self.writer.add_scalar('Loss/d_loss_lod0',
                                               losses_lod0['depth_loss'].mean() if losses_lod0 is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('Loss/sparse_loss_lod0',
                                               losses_lod0[
                                                   'sparse_loss'].mean() if losses_lod0 is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('Loss/color_loss_lod0',
                                               losses_lod0['color_fine_loss'].mean()
                                               if losses_lod0['color_fine_loss'] is not None else 0,
                                               self.iter_step)

                        self.writer.add_scalar('statis/psnr_lod0',
                                               losses_lod0['psnr'].mean()
                                               if losses_lod0['psnr'] is not None else 0,
                                               self.iter_step)

                        self.writer.add_scalar('param/variance_lod0',
                                               1. / torch.exp(self.variance_network_lod0.variance * 10),
                                               self.iter_step)
                        self.writer.add_scalar('param/eikonal_loss', losses_lod0['gradient_error_loss'].mean() if losses_lod0 is not None else 0,
                                               self.iter_step)

                    ######## - lod 1
                    if self.num_lods > 1:
                        self.writer.add_scalar('Loss/d_loss_lod1',
                                               losses_lod1['depth_loss'].mean() if losses_lod1 is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('Loss/sparse_loss_lod1',
                                               losses_lod1[
                                                   'sparse_loss'].mean() if losses_lod1 is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('Loss/color_loss_lod1',
                                               losses_lod1['color_fine_loss'].mean()
                                               if losses_lod1['color_fine_loss'] is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('statis/sdf_mean_lod1',
                                               losses_lod1['sdf_mean'].mean() if losses_lod1 is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('statis/psnr_lod1',
                                               losses_lod1['psnr'].mean()
                                               if losses_lod1['psnr'] is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('statis/sparseness_0.01_lod1',
                                               losses_lod1['sparseness_1'].mean()
                                               if losses_lod1['sparseness_1'] is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('statis/sparseness_0.02_lod1',
                                               losses_lod1['sparseness_2'].mean()
                                               if losses_lod1['sparseness_2'] is not None else 0,
                                               self.iter_step)
                        self.writer.add_scalar('param/variance_lod1',
                                               1. / torch.exp(self.variance_network_lod1.variance * 10),
                                               self.iter_step)

                    print(self.base_exp_dir)
                    print(
                        'iter:{:8>d} '
                        'loss = {:.4f} '
                        'd_loss_lod0 = {:.4f} '
                        'color_loss_lod0 = {:.4f} '
                        'sparse_loss_lod0= {:.4f} '
                        'd_loss_lod1 = {:.4f} '
                        'color_loss_lod1 = {:.4f} '
                        '  lr = {:.5f}'.format(
                            self.iter_step, loss,
                            losses_lod0['depth_loss'].mean() if losses_lod0 is not None else 0,
                            losses_lod0['color_fine_loss'].mean() if losses_lod0 is not None else 0,
                            losses_lod0['sparse_loss'].mean() if losses_lod0 is not None else 0,
                            losses_lod1['depth_loss'].mean() if losses_lod1 is not None else 0,
                            losses_lod1['color_fine_loss'].mean() if losses_lod1 is not None else 0,
                            self.optimizer.param_groups[0]['lr']))

                    print(colored('alpha_inter_ratio_lod0 = {:.4f} alpha_inter_ratio_lod1 = {:.4f}\n'.format(
                        alpha_inter_ratio_lod0, alpha_inter_ratio_lod1), 'green'))

                    if losses_lod0 is not None:
                        # print("[TEST]: weights_sum in print", losses_lod0['weights_sum'].mean())
                        # import ipdb; ipdb.set_trace()
                        print(
                            'iter:{:8>d} '
                            'variance = {:.5f} '
                            'weights_sum = {:.4f} '
                            'weights_sum_fg = {:.4f} '
                            'alpha_sum = {:.4f} '
                            'sparse_weight= {:.4f} '
                            'background_loss = {:.4f} '
                            'background_weight = {:.4f} '
                                .format(
                                self.iter_step,
                                losses_lod0['variance'].mean(),
                                losses_lod0['weights_sum'].mean(),
                                losses_lod0['weights_sum_fg'].mean(),
                                losses_lod0['alpha_sum'].mean(),
                                losses_lod0['sparse_weight'].mean(),
                                losses_lod0['fg_bg_loss'].mean(),
                                losses_lod0['fg_bg_weight'].mean(),
                            ))

                    if losses_lod1 is not None:
                        print(
                            'iter:{:8>d} '
                            'variance = {:.5f} '
                            ' weights_sum = {:.4f} '
                            'alpha_sum = {:.4f} '
                            'fg_bg_loss = {:.4f} '
                            'fg_bg_weight = {:.4f} '
                            'sparse_weight= {:.4f} '
                            'fg_bg_loss = {:.4f} '
                            'fg_bg_weight = {:.4f} '
                                .format(
                                self.iter_step,
                                losses_lod1['variance'].mean(),
                                losses_lod1['weights_sum'].mean(),
                                losses_lod1['alpha_sum'].mean(),
                                losses_lod1['fg_bg_loss'].mean(),
                                losses_lod1['fg_bg_weight'].mean(),
                                losses_lod1['sparse_weight'].mean(),
                                losses_lod1['fg_bg_loss'].mean(),
                                losses_lod1['fg_bg_weight'].mean(),
                            ))

                if self.iter_step % self.save_freq == 0:
                    self.save_checkpoint()

                if self.iter_step % self.val_freq == 0:
                    self.validate()

                # - ajust learning rate
                self.adjust_learning_rate()

    def adjust_learning_rate(self):
        # - ajust learning rate, cosine learning schedule
        learning_rate = (np.cos(np.pi * self.iter_step / self.end_iter) + 1.0) * 0.5 * 0.9 + 0.1
        learning_rate = self.learning_rate * learning_rate
        for g in self.optimizer.param_groups:
            g['lr'] = learning_rate

    def get_alpha_inter_ratio(self, start, end):
        if end == 0.0:
            return 1.0
        elif self.iter_step < start:
            return 0.0
        else:
            return np.min([1.0, (self.iter_step - start) / (end - start)])

    def file_backup(self):
        # copy python file
        dir_lis = self.conf['general.recording']
        os.makedirs(os.path.join(self.base_exp_dir, 'recording'), exist_ok=True)
        for dir_name in dir_lis:
            cur_dir = os.path.join(self.base_exp_dir, 'recording', dir_name)
            os.makedirs(cur_dir, exist_ok=True)
            files = os.listdir(dir_name)
            for f_name in files:
                if f_name[-3:] == '.py':
                    copyfile(os.path.join(dir_name, f_name), os.path.join(cur_dir, f_name))

        # copy configs
        copyfile(self.conf_path, os.path.join(self.base_exp_dir, 'recording', 'config.conf'))

    def load_checkpoint(self, checkpoint_name):

        def load_state_dict(network, checkpoint, comment):
            if network is not None:
                try:
                    pretrained_dict = checkpoint[comment]

                    model_dict = network.state_dict()

                    # 1. filter out unnecessary keys
                    pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
                    # 2. overwrite entries in the existing state dict
                    model_dict.update(pretrained_dict)
                    # 3. load the new state dict
                    network.load_state_dict(pretrained_dict)
                except:
                    print(colored(comment + " load fails", 'yellow'))

        checkpoint = torch.load(os.path.join(self.base_exp_dir, 'checkpoints', checkpoint_name),
                                map_location=self.device)

        load_state_dict(self.rendering_network_outside, checkpoint, 'rendering_network_outside')

        load_state_dict(self.sdf_network_lod0, checkpoint, 'sdf_network_lod0')
        load_state_dict(self.sdf_network_lod1, checkpoint, 'sdf_network_lod1')

        load_state_dict(self.pyramid_feature_network, checkpoint, 'pyramid_feature_network')
        load_state_dict(self.pyramid_feature_network_lod1, checkpoint, 'pyramid_feature_network_lod1')

        load_state_dict(self.variance_network_lod0, checkpoint, 'variance_network_lod0')
        load_state_dict(self.variance_network_lod1, checkpoint, 'variance_network_lod1')

        load_state_dict(self.rendering_network_lod0, checkpoint, 'rendering_network_lod0')
        load_state_dict(self.rendering_network_lod1, checkpoint, 'rendering_network_lod1')

        if self.restore_lod0:  # use the trained lod0 networks to initialize lod1 networks
            load_state_dict(self.sdf_network_lod1, checkpoint, 'sdf_network_lod0')
            load_state_dict(self.pyramid_feature_network_lod1, checkpoint, 'pyramid_feature_network')
            load_state_dict(self.rendering_network_lod1, checkpoint, 'rendering_network_lod0')

        if self.is_continue and (not self.restore_lod0):
            try:
                self.optimizer.load_state_dict(checkpoint['optimizer'])
            except:
                print(colored("load optimizer fails", "yellow"))
            self.iter_step = checkpoint['iter_step']
            self.val_step = checkpoint['val_step'] if 'val_step' in checkpoint.keys() else 0

        self.logger.info('End')

    def save_checkpoint(self):

        def save_state_dict(network, checkpoint, comment):
            if network is not None:
                checkpoint[comment] = network.state_dict()

        checkpoint = {
            'optimizer': self.optimizer.state_dict(),
            'iter_step': self.iter_step,
            'val_step': self.val_step,
        }

        save_state_dict(self.sdf_network_lod0, checkpoint, "sdf_network_lod0")
        save_state_dict(self.sdf_network_lod1, checkpoint, "sdf_network_lod1")

        save_state_dict(self.rendering_network_outside, checkpoint, 'rendering_network_outside')
        save_state_dict(self.rendering_network_lod0, checkpoint, "rendering_network_lod0")
        save_state_dict(self.rendering_network_lod1, checkpoint, "rendering_network_lod1")

        save_state_dict(self.variance_network_lod0, checkpoint, 'variance_network_lod0')
        save_state_dict(self.variance_network_lod1, checkpoint, 'variance_network_lod1')

        save_state_dict(self.pyramid_feature_network, checkpoint, 'pyramid_feature_network')
        save_state_dict(self.pyramid_feature_network_lod1, checkpoint, 'pyramid_feature_network_lod1')

        os.makedirs(os.path.join(self.base_exp_dir, 'checkpoints'), exist_ok=True)
        torch.save(checkpoint,
                   os.path.join(self.base_exp_dir, 'checkpoints', 'ckpt_{:0>6d}.pth'.format(self.iter_step)))

    def validate(self, idx=-1, resolution_level=-1):
        # validate image

        ic(self.iter_step, idx)
        self.logger.info('Validate begin')
        if idx < 0:
            idx = self.val_step
        self.val_step += 1

        try:
            batch = next(self.val_dataloader_iterator)
            # batch = self.val_dataloader_iterator.next()
        except:
            self.val_dataloader_iterator = iter(self.val_dataloader)  # reset
            
            batch = next(self.val_dataloader_iterator)


        background_rgb = None
        if self.use_white_bkgd:
            background_rgb = 1.0

        batch['batch_idx'] = torch.tensor([x for x in range(self.batch_size)])

        # - warmup params
        if self.num_lods == 1:
            alpha_inter_ratio_lod0 = self.get_alpha_inter_ratio(self.anneal_start_lod0, self.anneal_end_lod0)
        else:
            alpha_inter_ratio_lod0 = 1.
        alpha_inter_ratio_lod1 = self.get_alpha_inter_ratio(self.anneal_start_lod1, self.anneal_end_lod1)

        self.trainer(
            batch,
            background_rgb=background_rgb,
            alpha_inter_ratio_lod0=alpha_inter_ratio_lod0,
            alpha_inter_ratio_lod1=alpha_inter_ratio_lod1,
            iter_step=self.iter_step,
            save_vis=True,
            mode='val',
        )


    def export_mesh(self, idx=-1, resolution_level=-1):
        # validate image

        ic(self.iter_step, idx)
        self.logger.info('Validate begin')
        import time 
        start1 = time.time()
        if idx < 0:
            idx = self.val_step
            # idx = np.random.randint(len(self.val_dataset))
        self.val_step += 1

        try:
            batch = self.val_dataloader_iterator.next()
        except:
            self.val_dataloader_iterator = iter(self.val_dataloader)  # reset
            
            batch = self.val_dataloader_iterator.next()


        background_rgb = None
        if self.use_white_bkgd:
            background_rgb = 1.0

        batch['batch_idx'] = torch.tensor([x for x in range(self.batch_size)])

        # - warmup params
        if self.num_lods == 1:
            alpha_inter_ratio_lod0 = self.get_alpha_inter_ratio(self.anneal_start_lod0, self.anneal_end_lod0)
        else:
            alpha_inter_ratio_lod0 = 1.
        alpha_inter_ratio_lod1 = self.get_alpha_inter_ratio(self.anneal_start_lod1, self.anneal_end_lod1)
        end1 = time.time()
        print("time for getting data", end1 - start1)
        self.trainer(
            batch,
            background_rgb=background_rgb,
            alpha_inter_ratio_lod0=alpha_inter_ratio_lod0,
            alpha_inter_ratio_lod1=alpha_inter_ratio_lod1,
            iter_step=self.iter_step,
            save_vis=True,
            mode='export_mesh',
        )


if __name__ == '__main__':
    # torch.set_default_tensor_type('torch.cuda.FloatTensor')
    torch.set_default_dtype(torch.float32)
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', type=str, default='./confs/base.conf')
    parser.add_argument('--mode', type=str, default='train')
    parser.add_argument('--threshold', type=float, default=0.0)
    parser.add_argument('--is_continue', default=False, action="store_true")
    parser.add_argument('--is_restore', default=False, action="store_true")
    parser.add_argument('--is_finetune', default=False, action="store_true")
    parser.add_argument('--train_from_scratch', default=False, action="store_true")
    parser.add_argument('--restore_lod0', default=False, action="store_true")
    parser.add_argument('--local_rank', type=int, default=0)
    args = parser.parse_args()

    torch.cuda.set_device(args.local_rank)
    torch.backends.cudnn.benchmark = True  # ! make training 2x faster

    runner = Runner(args.conf, args.mode, args.is_continue, args.is_restore, args.restore_lod0,
                    args.local_rank, args.is_finetune)

    if args.mode == 'train':
        runner.train()
    elif args.mode == 'val':
        for i in range(len(runner.val_dataset)):
            runner.validate()
    elif args.mode == 'export_mesh':
        for i in range(len(runner.val_dataset)):
            runner.export_mesh()
