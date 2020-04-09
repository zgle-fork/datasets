# coding=utf-8
# Copyright 2020 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Tests for the Split API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow_datasets import testing
from tensorflow_datasets.core import proto
from tensorflow_datasets.core import splits
import tensorflow_datasets.public_api as tfds

RANGE_TRAIN = list(range(0, 2000))
RANGE_TEST = list(range(3000, 3200))
RANGE_VAL = list(range(6000, 6010))


class SplitDictTest(testing.TestCase):

  def test_num_shards(self):
    sd = splits.SplitDict("ds_name")
    sd.add(tfds.core.SplitInfo(name="train", shard_lengths=[1, 2, 3]))
    self.assertEqual(sd["train"].num_shards, 3)

    # When both values are set, shard_lengths has priority.
    sd = splits.SplitDict("ds_name")
    sd.add(tfds.core.SplitInfo(name="train", num_shards=3, shard_lengths=[1,]))
    self.assertEqual(sd["train"].num_shards, 1)

    # With legacy mode, use legacy value
    sd = splits.SplitDict("ds_name")
    sd.add(tfds.core.SplitInfo(name="train", num_shards=3))
    self.assertEqual(sd["train"].num_shards, 3)


class SplitsUnitTest(testing.TestCase):

  @classmethod
  def setUpClass(cls):
    super(SplitsUnitTest, cls).setUpClass()
    cls._splits = tfds.core.SplitDict("ds_name")
    cls._splits.add(tfds.core.SplitInfo(name="train", num_shards=10))
    cls._splits.add(tfds.core.SplitInfo(name="test", num_shards=2))
    cls._splits.add(tfds.core.SplitInfo(name="custom", num_shards=2))

  def test_split_slice_merge(self):

    # Slice, then merge
    train = tfds.Split.TRAIN
    test = tfds.Split.TEST
    split = test.subsplit(tfds.percent[30:40]) + train

    self.assertEqual(
        "{}".format(split),
        "(NamedSplit('test')(tfds.percent[30:40]) + NamedSplit('train'))"
    )

    # List sorted so always deterministic
    self.assertEqual(self._info(split), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(30, 40),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=None,
        ),
    ])

  def test_split_merge_slice(self):

    # Merge, then slice (then merge)
    split = tfds.Split.TEST + tfds.Split.TRAIN
    split = split.subsplit(tfds.percent[30:40])
    split = split + tfds.Split("custom").subsplit(tfds.percent[:15])

    # List sorted so always deterministic
    self.assertEqual(self._info(split), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="custom", num_shards=2),
            slice_value=slice(None, 15),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(30, 40),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(30, 40),
        ),
    ])

  def test_split_k(self):
    split = tfds.Split.TEST + tfds.Split.TRAIN
    split1, split2, split3 = split.subsplit(k=3)

    self.assertEqual(self._info(split1), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(0, 33),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(0, 33),
        ),
    ])

    self.assertEqual(self._info(split2), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(33, 66),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(33, 66),
        ),
    ])

    self.assertEqual(self._info(split3), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(66, 100),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(66, 100),
        ),
    ])

  def test_split_weighted(self):
    split = tfds.Split.TEST + tfds.Split.TRAIN
    split1, split2 = split.subsplit(weighted=[2, 1])

    self.assertEqual(self._info(split1), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(0, 66),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(0, 66),
        ),
    ])

    self.assertEqual(self._info(split2), [
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="test", num_shards=2),
            slice_value=slice(66, 100),
        ),
        splits.SlicedSplitInfo(
            split_info=tfds.core.SplitInfo(name="train", num_shards=10),
            slice_value=slice(66, 100),
        ),
    ])

  def test_split_equivalence(self):
    split = tfds.Split.TRAIN + tfds.Split.TEST

    # Different way of splitting should all return the same results

    # Take first half of the split
    a = self._info(split.subsplit(k=2)[0])
    b = self._info(split.subsplit([1, 1])[0])
    c = self._info(split.subsplit([5, 5])[0])
    d = self._info(split.subsplit(tfds.percent[0:50]))

    self.assertEqual(a, b)
    self.assertEqual(b, c)
    self.assertEqual(c, d)
    self.assertEqual(d, a)

    # Take the last third of the split
    a = self._info(split.subsplit(k=3)[-1])
    b = self._info(split.subsplit([2, 1])[-1])
    b = self._info(split.subsplit([33, 11, 22, 34])[-1])
    c = self._info(split.subsplit(tfds.percent[66:100]))

    self.assertEqual(a, b)
    self.assertEqual(b, c)
    self.assertEqual(c, a)

    train = tfds.Split.TRAIN
    # 20%, 20% and 60% of the training set (using weighted)
    split1_1, split1_2, split1_3 = train.subsplit([2, 2, 6])
    split1_1 = self._info(split1_1)
    split1_2 = self._info(split1_2)
    split1_3 = self._info(split1_3)
    # 20%, 20% and 60% of the training set (using percent)
    split2_1 = self._info(train.subsplit(tfds.percent[0:20]))
    split2_2 = self._info(train.subsplit(tfds.percent[20:40]))
    split2_3 = self._info(train.subsplit(tfds.percent[40:100]))
    self.assertEqual(split1_1, split2_1)
    self.assertEqual(split1_2, split2_2)
    self.assertEqual(split1_3, split2_3)

  def test_split_equality(self):
    test = tfds.Split.TEST
    train = tfds.Split.TRAIN

    with self.assertRaisesWithPredicateMatch(
        NotImplementedError,
        "Equality is not implemented between merged/sub splits."):
      _ = test.subsplit(tfds.percent[10:]) == test.subsplit(tfds.percent[10:])

    with self.assertRaisesWithPredicateMatch(
        NotImplementedError,
        "Equality is not implemented between merged/sub splits."):
      _ = test + train == test + train

    self.assertEqual(tfds.Split.TEST, tfds.Split.TEST)
    self.assertEqual(tfds.Split.TEST, "test")
    self.assertEqual("test", tfds.Split.TEST)

    self.assertNotEqual(train, test)
    self.assertNotEqual(train, train.subsplit(tfds.percent[:50]))
    self.assertNotEqual(train.subsplit(tfds.percent[:50]), train)

    # Explictly want to test the `!=` operator.
    self.assertFalse(tfds.Split.TRAIN != "train")  # pylint: disable=g-generic-assert

  def _info(self, split):
    read_instruction = split.get_read_instruction(self._splits)
    return read_instruction.get_list_sliced_split_info()


class SliceToMaskTest(testing.TestCase):

  def __getitem__(self, slice_value):
    return slice_value

  def test_slice_to_mask(self):
    s2p = splits.slice_to_percent_mask

    self.assertEqual(s2p(self[:]), [True] * 100)
    self.assertEqual(s2p(self[:60]), [True] * 60 + [False] * 40)
    self.assertEqual(s2p(self[60:]), [False] * 60 + [True] * 40)
    self.assertEqual(
        s2p(self[10:20]), [False] * 10 + [True] * 10 + [False] * 80)
    self.assertEqual(s2p(self[:-20]), [True] * 80 + [False] * 20)


class SplitsOffsetTest(testing.TestCase):

  def test_get_shard_id2num_examples(self):
    self.assertEqual(
        splits.get_shard_id2num_examples(num_shards=8, total_num_examples=80),
        [10, 10, 10, 10, 10, 10, 10, 10],
    )
    self.assertEqual(
        splits.get_shard_id2num_examples(num_shards=5, total_num_examples=553),
        [111, 111, 111, 110, 110],
    )

  def test_compute_mask_offsets(self):
    self.assertEqual(
        splits.compute_mask_offsets([1100, 500, 1100, 110]),
        [0, 0, 0, 0],
    )
    self.assertEqual(
        splits.compute_mask_offsets([1101, 500, 1100, 110]),
        [0, 1, 1, 1],
    )
    self.assertEqual(
        splits.compute_mask_offsets([87]),
        [0],
    )
    self.assertEqual(
        splits.compute_mask_offsets([1101, 501, 1113, 110]),
        [0, 1, 2, 15],
    )


class SplitsDictTest(testing.TestCase):

  @property
  def split_dict(self):
    sd = splits.SplitDict("ds_name")
    sd.add(tfds.core.SplitInfo(name="train", num_shards=10))
    sd.add(tfds.core.SplitInfo(name="test", num_shards=1))
    return sd

  # .add is implicitly tested, since s was created by calling .add
  def test_get(self):
    s = self.split_dict["train"]
    self.assertEqual("train", s.name)
    self.assertEqual(10, s.num_shards)

  def test_from_proto(self):
    sd = splits.SplitDict.from_proto(
        "ds_name", [proto.SplitInfo(name="validation", num_shards=5)])
    self.assertIn("validation", sd)
    self.assertNotIn("train", sd)
    self.assertNotIn("test", sd)

  def test_to_proto(self):
    sd = self.split_dict
    sdp = sd.to_proto()

    self.assertEqual("test", sdp[0].name)
    self.assertEqual(1, sdp[0].num_shards)

    self.assertEqual("train", sdp[1].name)
    self.assertEqual(10, sdp[1].num_shards)

  def test_bool(self):
    sd = splits.SplitDict("ds_name")
    self.assertFalse(sd)  # Empty split is False
    sd.add(tfds.core.SplitInfo(name="train", num_shards=10))
    self.assertTrue(sd)  # Non-empty split is True

  def test_check_splits_equals(self):
    s1 = splits.SplitDict("ds_name")
    s1.add(tfds.core.SplitInfo(name="train", num_shards=10))
    s1.add(tfds.core.SplitInfo(name="test", num_shards=3))

    s2 = splits.SplitDict("ds_name")
    s2.add(tfds.core.SplitInfo(name="train", num_shards=10))
    s2.add(tfds.core.SplitInfo(name="test", num_shards=3))

    s3 = splits.SplitDict("ds_name")
    s3.add(tfds.core.SplitInfo(name="train", num_shards=10))
    s3.add(tfds.core.SplitInfo(name="test", num_shards=3))
    s3.add(tfds.core.SplitInfo(name="valid", num_shards=0))

    s4 = splits.SplitDict("ds_name")
    s4.add(tfds.core.SplitInfo(name="train", num_shards=11))
    s4.add(tfds.core.SplitInfo(name="test", num_shards=3))

    self.assertTrue(splits.check_splits_equals(s1, s1))
    self.assertTrue(splits.check_splits_equals(s1, s2))
    self.assertFalse(splits.check_splits_equals(s1, s3))  # Not same names
    self.assertFalse(splits.check_splits_equals(s1, s4))  # Nb of shards !=

  def test_split_overwrite(self):
    s1 = splits.SplitDict("ds_name")
    s1.add(tfds.core.SplitInfo(name="train", shard_lengths=[15]))

    s2 = splits.SplitDict("ds_name")
    s2.add(tfds.core.SplitInfo(name="train", shard_lengths=[15]))

    self.assertTrue(splits.check_splits_equals(s1, s2))

    # Modifying num_shards should also modify the underlying proto
    s2["train"].shard_lengths = [5, 5, 5]
    self.assertEqual(s2["train"].shard_lengths, [5, 5, 5])
    self.assertEqual(s2["train"].get_proto().shard_lengths, [5, 5, 5])
    self.assertFalse(splits.check_splits_equals(s1, s2))


class SplitsSubsplitTest(testing.TestCase):

  @classmethod
  def setUpClass(cls):
    super(SplitsSubsplitTest, cls).setUpClass()
    cls._builder = testing.DummyDatasetSharedGenerator(
        data_dir=testing.make_tmp_dir())
    cls._builder.download_and_prepare()

  def test_sub_split_num_examples(self):
    s = self._builder.info.splits
    self.assertEqual(s["train[75%:]"].num_examples, 5)
    self.assertEqual(s["train[:75%]"].num_examples, 15)
    self.assertEqual(
        s["train"].num_examples,
        s["train[75%:]"].num_examples + s["train[:75%]"].num_examples,
    )

    self.assertEqual(s["test[75%:]"].num_examples, 2)
    self.assertEqual(s["test[:75%]"].num_examples, 8)
    self.assertEqual(
        s["test"].num_examples,
        s["test[75%:]"].num_examples + s["test[:75%]"].num_examples,
    )

  def test_sub_split_file_instructions(self):
    fi = self._builder.info.splits["train[75%:]"].file_instructions
    self.assertEqual(fi, [{
        "filename":
            "dummy_dataset_shared_generator-train.tfrecord-00000-of-00001",
        "skip": 15,
        "take": -1,
    }])

  def test_split_file_instructions(self):
    fi = self._builder.info.splits["train"].file_instructions
    self.assertEqual(fi, [{
        "filename":
            "dummy_dataset_shared_generator-train.tfrecord-00000-of-00001",
        "skip": 0,
        "take": -1,
    }])

  def test_sub_split_wrong_key(self):
    with self.assertRaisesWithPredicateMatch(
        ValueError, "Unknown split \"unknown\""):
      _ = self._builder.info.splits["unknown"]


if __name__ == "__main__":
  testing.test_main()
