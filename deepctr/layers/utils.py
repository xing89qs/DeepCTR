# -*- coding:utf-8 -*-
"""

Author:
    Weichen Shen,wcshen1994@163.com

"""
import tensorflow as tf

class NoMask(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super(NoMask, self).__init__(**kwargs)

    def build(self, input_shape):
        # Be sure to call this somewhere!
        super(NoMask, self).build(input_shape)

    def call(self, x, mask=None, **kwargs):
        return x

    def compute_mask(self, inputs, mask):
        return None


class Hash(tf.keras.layers.Layer):
    """
    hash the input to [0,num_buckets)
    if mask_zero = True,0 or 0.0 will be set to 0,other value will be set in range[1,num_buckets)
    """

    def __init__(self, num_buckets, mask_zero=False, **kwargs):
        self.num_buckets = num_buckets
        self.mask_zero = mask_zero
        super(Hash, self).__init__(**kwargs)

    def build(self, input_shape):
        # Be sure to call this somewhere!
        super(Hash, self).build(input_shape)

    def call(self, x, mask=None, **kwargs):
        if x.dtype != tf.string:
            x = tf.as_string(x, )
        try:
            hash_x = tf.string_to_hash_bucket_fast(x, self.num_buckets if not self.mask_zero else self.num_buckets - 1,
                                                   name=None)  # weak hash
        except:
            hash_x = tf.strings.to_hash_bucket_fast(x, self.num_buckets if not self.mask_zero else self.num_buckets - 1,
                                                    name=None)  # weak hash
        if self.mask_zero:
            mask_1 = tf.cast(tf.not_equal(x, "0"), 'int64')
            mask_2 = tf.cast(tf.not_equal(x, "0.0"), 'int64')
            mask = mask_1 * mask_2
            hash_x = (hash_x + 1) * mask
        return hash_x

    def compute_mask(self, inputs, mask):
        return None

    def get_config(self, ):
        config = {'num_buckets': self.num_buckets, 'mask_zero': self.mask_zero}
        base_config = super(Hash, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


class Linear(tf.keras.layers.Layer):

    def __init__(self, l1_reg=0.0, l2_reg=0.0, mode=0, use_bias=False, out_shape=None, **kwargs):

        self.l2_reg = l2_reg
        self.l1_reg = l1_reg
        # self.l2_reg = tf.contrib.layers.l2_regularizer(float(l2_reg_linear))
        if mode not in [0, 1, 2]:
            raise ValueError("mode must be 0,1 or 2")
        self.mode = mode
        self.out_shape = out_shape
        self.use_bias = use_bias
        super(Linear, self).__init__(**kwargs)

    def build(self, input_shape):
        if self.use_bias:
            self.bias = self.add_weight(name='linear_bias',
                                        shape=(self.out_shape,),
                                        initializer=tf.keras.initializers.Zeros(),
                                        trainable=True)
        if self.mode == 0:
            self.kernel = self.add_weight(
                'linear_kernel',
                shape=[int(input_shape[-1]), self.out_shape],
                initializer=tf.keras.initializers.glorot_normal(),
                regularizer=tf.keras.regularizers.l1_l2(self.l1_reg, self.l2_reg),
                trainable=True)
        if self.mode == 1:
            self.kernel = self.add_weight(
                'linear_kernel',
                shape=[int(input_shape[-1]), self.out_shape],
                initializer=tf.keras.initializers.glorot_normal(),
                regularizer=tf.keras.regularizers.l1_l2(self.l1_reg, self.l2_reg),
                trainable=True)
        elif self.mode == 2:
            self.kernel = [self.add_weight(
                'linear_kernel',
                shape=[int(input_shape[i][-1]), self.out_shape],
                initializer=tf.keras.initializers.glorot_normal(),
                regularizer=tf.keras.regularizers.l1_l2(self.l1_reg, self.l2_reg),
                trainable=True) for i in range(len(input_shape))]

        super(Linear, self).build(input_shape)  # Be sure to call this somewhere!

    def call(self, inputs, **kwargs):
        if self.mode == 0:
            sparse_input = inputs
            fc = tf.tensordot(sparse_input, self.kernel, axes=(-1, 0))
            linear_logit = fc
        elif self.mode == 1:
            dense_input = inputs
            fc = tf.expand_dims(tf.matmul(dense_input, self.kernel), axis=1)
            linear_logit = fc
        else:
            sparse_input, dense_input = inputs
            fc = tf.tensordot(sparse_input, self.kernel[0], axes=(-1, 0))
            linear_logit = tf.expand_dims(tf.matmul(dense_input, self.kernel[1]), axis=1) + fc
        if self.use_bias:
            linear_logit += self.bias

        return linear_logit

    def compute_output_shape(self, input_shape):
        return (None, self.out_shape)

    def compute_mask(self, inputs, mask):
        return None

    def get_config(self, ):
        config = {'mode': self.mode, 'l2_reg': self.l2_reg, 'use_bias': self.use_bias}
        base_config = super(Linear, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


def concat_func(inputs, axis=-1, mask=False):
    if not mask:
        inputs = list(map(NoMask(), inputs))
    if len(inputs) == 1:
        return inputs[0]
    else:
        return tf.keras.layers.Concatenate(axis=axis)(inputs)


def reduce_mean(input_tensor,
                axis=None,
                keep_dims=False,
                name=None,
                reduction_indices=None):
    if tf.__version__ < '2.0.0':
        return tf.reduce_mean(input_tensor,
                              axis=axis,
                              keep_dims=keep_dims,
                              name=name,
                              reduction_indices=reduction_indices)
    else:
        return tf.reduce_mean(input_tensor,
                              axis=axis,
                              keepdims=keep_dims,
                              name=name)


def reduce_sum(input_tensor,
               axis=None,
               keep_dims=False,
               name=None,
               reduction_indices=None):
    if tf.__version__ < '2.0.0':
        return tf.reduce_sum(input_tensor,
                             axis=axis,
                             keep_dims=keep_dims,
                             name=name,
                             reduction_indices=reduction_indices)
    else:
        return tf.reduce_sum(input_tensor,
                             axis=axis,
                             keepdims=keep_dims,
                             name=name)


def reduce_max(input_tensor,
               axis=None,
               keep_dims=False,
               name=None,
               reduction_indices=None):
    if tf.__version__ < '2.0.0':
        return tf.reduce_max(input_tensor,
                             axis=axis,
                             keep_dims=keep_dims,
                             name=name,
                             reduction_indices=reduction_indices)
    else:
        return tf.reduce_max(input_tensor,
                             axis=axis,
                             keepdims=keep_dims,
                             name=name)


def div(x, y, name=None):
    if tf.__version__ < '2.0.0':
        return tf.div(x, y, name=name)
    else:
        return tf.divide(x, y, name=name)


def softmax(logits, dim=-1, name=None):
    if tf.__version__ < '2.0.0':
        return tf.nn.softmax(logits, dim=dim, name=name)
    else:
        return tf.nn.softmax(logits, axis=dim, name=name)


class Add(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super(Add, self).__init__(**kwargs)

    def build(self, input_shape):
        # Be sure to call this somewhere!
        super(Add, self).build(input_shape)

    def call(self, inputs, **kwargs):
        if not isinstance(inputs, list):
            return inputs
        if len(inputs) == 1:
            return inputs[0]
        if len(inputs) == 0:
            return tf.constant([[0.0]])

        return tf.keras.layers.add(inputs)


def add_func(inputs):
    return Add()(inputs)
