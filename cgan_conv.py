from nets import *
from datas import *
from tools import *
import time


# 28x28x11: 手写体x和one-hot
def conv_concat(x, y):
    batch_size = tf.shape(x)[0]
    y = tf.reshape(y, [batch_size, 1, 1, 10])
    return tf.concat([x, y * tf.ones([batch_size, 28, 28, 10])], 3)  # 28x28x11


class CGAN():

    def __init__(self, generator, discriminator, data):
        self.generator = generator
        self.discriminator = discriminator
        self.data = data

        # data
        self.z_dim = self.data.z_dim
        self.y_dim = self.data.y_dim  # condition
        self.size = self.data.size
        self.channel = self.data.channel

        self.X = tf.placeholder(tf.float32, shape=[None, self.size, self.size, self.channel])
        self.y = tf.placeholder(tf.float32, shape=[None, self.y_dim])
        self.z = tf.placeholder(tf.float32, shape=[None, self.z_dim])

        # 这里是和DCGAN的不同点 #
        self.G_sample = self.generator(concat(self.z, self.y))
        self.D_real, _ = self.discriminator(conv_concat(self.X, self.y))
        self.D_fake, _ = self.discriminator(conv_concat(self.G_sample, self.y), reuse=True)
        # 这里是和DCGAN的不同点 #

        # loss
        self.D_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_real, labels=tf.ones_like(
            self.D_real))) + tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_fake, labels=tf.zeros_like(self.D_fake)))
        self.G_loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_fake, labels=tf.ones_like(self.D_fake)))

        # solver
        self.D_solver = tf.train.AdamOptimizer().minimize(self.D_loss, var_list=self.discriminator.vars)
        self.G_solver = tf.train.AdamOptimizer().minimize(self.G_loss, var_list=self.generator.vars)

        # saver
        self.saver = tf.train.Saver()

        # session
        gpu_options = tf.GPUOptions(allow_growth=True)
        self.sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))

    def train(self, sample_dir, ckpt_dir, training_epoches=1000000, batch_size=64):
        self.sess.run(tf.global_variables_initializer())

        # 固定的噪声
        fixed_n = 3
        fixed_y = sample_y(fixed_n * fixed_n, self.y_dim, ind=self.data.y_dim)
        fixed_z = sample_z(fixed_n * fixed_n, self.z_dim)

        for epoch in range(training_epoches):
            # update D
            X_b, y_b = self.data(batch_size)
            self.sess.run(self.D_solver, feed_dict={self.X: X_b, self.y: y_b, self.z: sample_z(batch_size, self.z_dim)})

            # update G
            k = 1
            for _ in range(k):
                self.sess.run(self.G_solver, feed_dict={self.y: y_b, self.z: sample_z(batch_size, self.z_dim)})

            # save img, model. print loss
            if epoch % 100 == 0 or epoch < 100:
                D_loss_curr = self.sess.run(self.D_loss, feed_dict={self.X: X_b, self.y: y_b, self.z: sample_z(batch_size, self.z_dim)})
                G_loss_curr = self.sess.run(self.G_loss, feed_dict={self.y: y_b, self.z: sample_z(batch_size, self.z_dim)})
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime((time.time()))),
                      'Iter: {}; D loss: {:.4}; G_loss: {:.4}'.format(epoch, D_loss_curr, G_loss_curr))

            if save_imgae(epoch):
                samples = self.sess.run(self.G_sample, feed_dict={self.y: fixed_y, self.z: fixed_z})

                fig = self.data.data2fig(samples, size=fixed_n)
                plt.savefig('{}/{}.png'.format(sample_dir, str(epoch)), bbox_inches='tight')
                plt.close(fig)

            if epoch % 100000 == 0 and epoch > 0:
                self.saver.save(self.sess, os.path.join(ckpt_dir, "cgan_conv.ckpt"))


if __name__ == '__main__':

    # 生成的图片的目录
    sample_dir = 'Samples/mnist_cgan_conv'
    make_dir_if_noe_exist(sample_dir)
    ckpt_dir = 'Ckpts/mnist_cgan_conv'
    make_dir_if_noe_exist(ckpt_dir)

    # 生成器
    generator = G_conv_mnist()
    # 判别器
    discriminator = D_conv_mnist()
    # 数据
    data = mnist()

    # run
    cgan = CGAN(generator, discriminator, data)
    cgan.train(sample_dir, ckpt_dir, training_epoches=500000)
