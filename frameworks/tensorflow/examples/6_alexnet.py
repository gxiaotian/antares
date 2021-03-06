#!/usr/bin/env python3

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import tensorflow as tf
from tensorflow.contrib import antares

if tf.version.VERSION.startswith('2.'):
  tf = tf.compat.v1
  tf.disable_eager_execution()


def create_param(name, shape):
  return tf.get_variable(name, shape, tf.float32, initializer=tf.truncated_normal_initializer(stddev=0.001), trainable=True)

input_tensor = tf.get_variable('input_tensor', [64, 3, 227, 227], tf.float32, initializer=tf.initializers.ones(tf.float32), trainable=False)

output_logits = antares.make_op(ir=f'''
  conv_0[N, F, HO, WO] +=! input_tensor[N, C, HO * 4 + KH, WO * 4 + KW] * const_0_[KH, KW, C, F] where HO in 55, WO in 55;
  mpool_0[N, C, HO, WO ] >=! conv_0[N, C, HO * 2 + KH, WO * 2 + KW].call(`max`, [0.0]) where HO in 27, WO in 27, KH in 3, KW in 3;
  conv_1[N, F, HO, WO] +=! mpool_0[N, C, -2 + HO + KH, -2 + WO + KW].when([-2 + HO + KH >= 0, -2 + HO + KH < 27, -2 + WO + KW >= 0, -2 + WO + KW < 27], 0.0) * const_1_[KH, KW, C, F] where HO in 27, WO in 27;
  mpool_1[N, C, HO, WO ] >=! conv_1[N, C, HO * 2 + KH, WO * 2 + KW].call(`max`, [0.0]) where HO in 13, WO in 13, KH in 3, KW in 3;
  conv_2[N, F, HO, WO] +=! mpool_1[N, C, -1 + HO + KH, -1 + WO + KW].when([-1 + HO + KH >= 0, -1 + HO + KH < 13, -1 + WO + KW >= 0, -1 + WO + KW < 13], 0.0) * const_2_[KH, KW, C, F] where HO in 13, WO in 13;
  conv_3[N, F, HO, WO] +=! conv_2[N, C, -1 + HO + KH, -1 + WO + KW].call(`max`, [0.0]).when([-1 + HO + KH >= 0, -1 + HO + KH < 13, -1 + WO + KW >= 0, -1 + WO + KW < 13], 0.0) * const_3_[KH, KW, C, F] where HO in 13, WO in 13;
  mpool_2[N, C, HO, WO] >=! conv_3[N, C, HO * 2 + KH, WO * 2 + KW].call(`max`, [0.0]) where HO in 6, WO in 6, KH in 3, KW in 3;
  reshape_0[N0, N1] = mpool_2[N0, N1 // 36 % 256, N1 // 6 % 6, N1 % 6] where N1 in 9216;
  dense_0[N, M] +=! reshape_0[N, K] * const_5_[K, M];
  dense_1[N, M] +=! dense_0[N, K].call(`max`, [0.0]) * const_6_[K, M];
  dense_2[N, M] +=! dense_1[N, K].call(`max`, [0.0]) * const_7_[K, M];
''', feed_dict={
  'input_tensor': input_tensor,
  'const_0_': create_param('const_0_', [11, 11, 3, 64]),
  'const_1_': create_param('const_1_', [5, 5, 64, 192]),
  'const_2_': create_param('const_2_', [3, 3, 192, 384]),
  'const_3_': create_param('const_3_', [3, 3, 384, 256]),
  'const_4_': create_param('const_4_', [3, 3, 256, 256]),
  'const_5_': create_param('const_5_', [9216, 4096]),
  'const_6_': create_param('const_6_', [4096, 4096]),
  'const_7_': create_param('const_7_', [4096, 1000]),
}).emit()

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
with tf.Session(config=config) as sess:
  sess.run(tf.global_variables_initializer())
  print('Result = %s' % sess.run([output_logits]))

