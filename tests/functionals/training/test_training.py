"""Unit tests for training functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pytest
import torch
import yaml

from panseg import FILE_CONFIG_TRAIN_YAML
from panseg.functionals.training.h5dataset import HDF5Dataset
from panseg.functionals.training.model import UNet2D
from panseg.functionals.training.train import (
    create_datasets,
    create_model_config,
    find_h5_files,
    unet_training,
    zero_mean_unit_variance,
)


def _write_checkpoints(mock_trainer_class, checkpoint_dir, make_states=None):
    """Let the mocked UNetTrainer leave checkpoint files behind like the real one.

    `unet_training` loads the packaged weights to generate the bioimageio test
    tensors, so a checkpoint has to exist after `train()` returns.
    """

    def _train():
        model = mock_trainer_class.call_args.kwargs["model"]
        if make_states is None:
            states = {
                "best_checkpoint.pytorch": model.state_dict(),
                "last_checkpoint.pytorch": model.state_dict(),
            }
        else:
            states = make_states(model)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        for name, state in states.items():
            torch.save(state, checkpoint_dir / name)

    mock_trainer_class.return_value.train.side_effect = _train


class TestFindH5Files:
    """Tests for find_h5_files function."""

    def test_find_h5_files_with_valid_directory(self):
        """Test finding h5 files in a valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with different extensions
            test_files = [
                temp_path / "test1.h5",
                temp_path / "test2.hdf",
                temp_path / "test3.hdf5",
                temp_path / "test4.hd5",
                temp_path / "test5.txt",  # Should not be found
            ]

            for file in test_files:
                file.touch()

            found_files = find_h5_files(temp_path)

            # Should find 4 h5-type files
            assert len(found_files) == 4

            # Check that only h5-type files are found
            found_names = [f.name for f in found_files]
            assert "test1.h5" in found_names
            assert "test2.hdf" in found_names
            assert "test3.hdf5" in found_names
            assert "test4.hd5" in found_names
            assert "test5.txt" not in found_names

    def test_find_h5_files_empty_directory(self):
        """Test finding h5 files in an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            found_files = find_h5_files(temp_dir)
            assert len(found_files) == 0

    def test_find_h5_files_invalid_directory(self):
        """Test finding h5 files with invalid directory."""
        with pytest.raises(AssertionError):
            find_h5_files("/non/existent/directory")


class TestCreateModelConfig:
    """Tests for create_model_config function."""

    def test_create_model_config_2d(self):
        """Test creating model config for 2D UNet."""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = Path(temp_dir) / "test_checkpoint"

            create_model_config(
                checkpoint_dir=checkpoint_dir,
                in_channels=1,
                out_channels=2,
                patch_size=[64, 64],
                dimensionality="2D",
                layer_order="bcr",
                sparse=False,
                f_maps=[16, 32, 64],
                max_num_iters=1000,
            )

            # Check that directory was created
            assert checkpoint_dir.exists()

            # Check that config file was created
            config_path = checkpoint_dir / FILE_CONFIG_TRAIN_YAML
            assert config_path.exists()

            # Check config content
            with open(config_path, "r") as f:
                config = yaml.load(f, Loader=yaml.FullLoader)

            assert config["model"]["in_channels"] == 1
            assert config["model"]["out_channels"] == 2
            assert config["model"]["f_maps"] == [16, 32, 64]
            assert config["model"]["name"] == "UNet2D"
            assert config["model"]["final_sigmoid"] is True  # not sparse
            assert config["trainer"]["checkpoint_dir"] == str(checkpoint_dir)
            assert config["trainer"]["max_num_iterations"] == 1000

    def test_create_model_config_3d(self):
        """Test creating model config for 3D UNet."""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = Path(temp_dir) / "test_checkpoint"

            create_model_config(
                checkpoint_dir=checkpoint_dir,
                in_channels=1,
                out_channels=3,
                patch_size=[32, 64, 64],
                dimensionality="3D",
                layer_order="bcr",
                sparse=True,
                f_maps=[8, 16, 32],
                max_num_iters=2000,
            )

            config_path = checkpoint_dir / FILE_CONFIG_TRAIN_YAML
            with open(config_path, "r") as f:
                config = yaml.load(f, Loader=yaml.FullLoader)

            assert config["model"]["name"] == "UNet3D"
            assert config["model"]["final_sigmoid"] is False  # sparse
            assert config["trainer"]["max_num_iterations"] == 2000
            assert config["loaders"]["train"]["slice_builder"]["patch_shape"] == [
                32,
                64,
                64,
            ]
            assert config["loaders"]["train"]["slice_builder"]["stride_shape"] == [
                16,
                32,
                32,
            ]


class TestCreateDatasets:
    """Tests for create_datasets function."""

    def test_create_datasets_train_3D(self):
        """Test creating training datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            train_dir = temp_path / "train"
            train_dir.mkdir()

            # Create dummy h5 files
            for i in range(3):
                h5_file = train_dir / f"data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(10, 88, 88))

            datasets = create_datasets(str(temp_path), "train", (8, 64, 64), "3D")

            assert len(datasets) == 3
            assert len(datasets[0]) == 8

            for dataset in datasets:
                assert isinstance(dataset, HDF5Dataset)

    def test_create_datasets_train_3Dc(self):
        """Test creating training datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            train_dir = temp_path / "train"
            train_dir.mkdir()

            # Create dummy h5 files
            for i in range(3):
                h5_file = train_dir / f"data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(3, 10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(10, 88, 88))

            datasets = create_datasets(str(temp_path), "train", (8, 64, 64), "3D")

            assert len(datasets) == 3
            assert len(datasets[0]) == 8

            for dataset in datasets:
                assert isinstance(dataset, HDF5Dataset)

    def test_create_datasets_train_2Dc(self):
        """Test creating training datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            train_dir = temp_path / "train"
            train_dir.mkdir()

            # Create dummy h5 files
            for i in range(3):
                h5_file = train_dir / f"data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(88, 88))

            datasets = create_datasets(str(temp_path), "train", (1, 64, 64), "2D")

            assert len(datasets) == 3
            assert len(datasets[0]) == 4

            for dataset in datasets:
                assert isinstance(dataset, HDF5Dataset)

    def test_create_datasets_train_2D(self):
        """Test creating training datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            train_dir = temp_path / "train"
            train_dir.mkdir()

            # Create dummy h5 files
            for i in range(3):
                h5_file = train_dir / f"data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(88, 88))
                    f.create_dataset("label", data=np.random.rand(88, 88))

            datasets = create_datasets(str(temp_path), "train", (1, 64, 64), "2D")

            assert len(datasets) == 3
            assert len(datasets[0]) == 4

            for dataset in datasets:
                assert isinstance(dataset, HDF5Dataset)

    def test_create_datasets_val_3D(self):
        """Test creating validation datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            val_dir = temp_path / "val"
            val_dir.mkdir()

            # Create dummy h5 files
            for i in range(2):
                h5_file = val_dir / f"val_data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(10, 88, 88))

            datasets = create_datasets(str(temp_path), "val", (8, 64, 64), "3D")

            assert len(datasets) == 2

    def test_create_datasets_val_2Dc(self):
        """Test creating validation datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            val_dir = temp_path / "val"
            val_dir.mkdir()

            # Create dummy h5 files
            for i in range(2):
                h5_file = val_dir / f"val_data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(88, 88))

            datasets = create_datasets(str(temp_path), "val", (1, 64, 64), "2D")

            assert len(datasets) == 2

    def test_create_datasets_val_2D(self):
        """Test creating validation datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            val_dir = temp_path / "val"
            val_dir.mkdir()

            # Create dummy h5 files
            for i in range(2):
                h5_file = val_dir / f"val_data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(88, 88))
                    f.create_dataset("label", data=np.random.rand(88, 88))

            datasets = create_datasets(str(temp_path), "val", (1, 64, 64), "2D")

            assert len(datasets) == 2

    def test_create_datasets_invalid_phase(self):
        """Test creating datasets with invalid phase."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            val_dir = temp_path / "val"
            val_dir.mkdir()

            # Create dummy h5 files
            for i in range(2):
                h5_file = val_dir / f"val_data_{i}.h5"
                with h5py.File(h5_file, "w") as f:
                    f.create_dataset("raw", data=np.random.rand(10, 88, 88))
                    f.create_dataset("label", data=np.random.rand(10, 88, 88))

            with pytest.raises(AssertionError):
                create_datasets(str(temp_dir), "invalid_phase", (8, 64, 64), "3D")


class TestUnetTraining:
    """Tests for unet_training function."""

    @patch("panseg.functionals.training.train.test_model")
    @patch("panseg.functionals.training.train.make_model_description")
    @patch("panseg.functionals.training.train.UNetTrainer")
    @patch("panseg.functionals.training.train.create_datasets")
    @patch("panseg.functionals.training.train.create_model_config")
    @patch("panseg.functionals.training.train.DataLoader")
    @patch("panseg.functionals.training.train.ConcatDataset")
    def test_unet_training_2d(
        self,
        mock_concat,
        mock_data_loader,
        mock_create_config,
        mock_create_datasets,
        mock_trainer,
        mock_model_desc,
        mock_test_model,
        tmp_path,
    ):
        """Test UNet training for 2D case."""
        mock_dataset = MagicMock()
        mock_dataset.__len__.return_value = 10  # Mock non-empty dataset
        mock_create_datasets.return_value = [mock_dataset]

        mock_trainer_instance = MagicMock()
        mock_trainer.return_value = mock_trainer_instance

        _write_checkpoints(mock_trainer, tmp_path / "test_model_2d")

        mock_data_loader.return_value = [
            (  # b, c, z,  x,  y
                torch.from_numpy(np.random.rand(1, 1, 1, 64, 64)).type(torch.float32),
                None,
            )
        ]

        mock_create_config.side_effect = create_model_config

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "train").mkdir()
        (dataset_dir / "val").mkdir()

        # Test parameters
        model_name = "test_model_2d"

        # Patch PATH_PANSEG_MODELS to use temp directory
        with patch("panseg.functionals.training.train.PATH_PANSEG_MODELS", tmp_path):
            with patch("panseg.core.zoo.PATH_PANSEG_MODELS", tmp_path):
                unet_training(
                    dataset_dir=str(dataset_dir),
                    model_name=model_name,
                    in_channels=1,
                    out_channels=1,
                    feature_maps=(16, 32, 64),
                    patch_size=(1, 64, 64),
                    max_num_iters=100,
                    dimensionality="2D",
                    sparse=False,
                    device="cpu",
                )

        mock_trainer_instance.train.assert_called_once()
        mock_create_config.assert_called_once()

        # Verify that create_datasets was called for both train and val
        assert mock_create_datasets.call_count == 2

        mock_model_desc.assert_called_once()
        assert (tmp_path / model_name / "test_in.npy").exists()
        assert (tmp_path / model_name / "test_out.npy").exists()

    @patch("panseg.functionals.training.train.test_model")
    @patch("panseg.functionals.training.train.make_model_description")
    @patch("panseg.functionals.training.train.UNetTrainer")
    @patch("panseg.functionals.training.train.create_datasets")
    @patch("panseg.functionals.training.train.create_model_config")
    @patch("panseg.functionals.training.train.DataLoader")
    @patch("panseg.functionals.training.train.ConcatDataset")
    def test_unet_training_3d(
        self,
        mock_concat,
        mock_data_loader,
        mock_create_config,
        mock_create_datasets,
        mock_trainer,
        mock_model_desc,
        mock_test_model,
        tmp_path,
    ):
        """Test UNet training for 3D case."""
        mock_dataset = MagicMock()
        mock_dataset.__len__.return_value = 10  # Mock non-empty dataset
        mock_create_datasets.return_value = [mock_dataset]

        mock_trainer_instance = MagicMock()
        mock_trainer.return_value = mock_trainer_instance

        _write_checkpoints(mock_trainer, tmp_path / "test_model_3d")

        mock_data_loader.return_value = [
            (
                torch.from_numpy(np.random.rand(1, 1, 16, 64, 64)).type(torch.float32),
                None,
            )
        ]

        mock_create_config.side_effect = create_model_config

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "train").mkdir()
        (dataset_dir / "val").mkdir()

        # Test parameters
        model_name = "test_model_3d"

        # Patch PATH_PANSEG_MODELS to use temp directory
        with patch("panseg.functionals.training.train.PATH_PANSEG_MODELS", tmp_path):
            with patch("panseg.core.zoo.PATH_PANSEG_MODELS", tmp_path):
                unet_training(
                    dataset_dir=str(dataset_dir),
                    model_name=model_name,
                    in_channels=1,
                    out_channels=1,
                    feature_maps=(16, 32, 64),
                    patch_size=(8, 64, 64),
                    max_num_iters=100,
                    dimensionality="3D",
                    sparse=True,
                    device="cpu",
                )

        mock_trainer_instance.train.assert_called_once()
        mock_create_config.assert_called_once()

        # Verify that create_datasets was called for both train and val
        assert mock_create_datasets.call_count == 2

        mock_model_desc.assert_called_once()
        assert mock_model_desc.call_args.kwargs["final_sigmoid"] is False
        assert (tmp_path / model_name / "test_in.npy").exists()
        assert (tmp_path / model_name / "test_out.npy").exists()

    @patch("panseg.functionals.training.train.test_model")
    @patch("panseg.functionals.training.train.make_model_description")
    @patch("panseg.functionals.training.train.UNetTrainer")
    @patch("panseg.functionals.training.train.create_datasets")
    @patch("panseg.functionals.training.train.create_model_config")
    @patch("panseg.functionals.training.train.DataLoader")
    @patch("panseg.functionals.training.train.ConcatDataset")
    def test_test_tensors_reproduced_from_packaged_weights(
        self,
        mock_concat,
        mock_data_loader,
        mock_create_config,
        mock_create_datasets,
        mock_trainer,
        mock_model_desc,
        mock_test_model,
        tmp_path,
    ):
        """test_out must come from the packaged weights and test_in must be raw.

        Regression test: test_out used to be generated from the live model (the
        last training state) while the package shipped `best_checkpoint.pytorch`,
        so `bioimageio.core.test_model` could not reproduce the test outputs.
        test_in used to be stored pre-normalized, although the model description
        declares ZeroMeanUnitVariance preprocessing.
        """
        torch.manual_seed(0)

        mock_dataset = MagicMock()
        mock_dataset.__len__.return_value = 10
        mock_create_datasets.return_value = [mock_dataset]
        mock_create_config.side_effect = create_model_config

        loader_batch = torch.from_numpy(
            np.random.rand(1, 1, 1, 64, 64).astype("float32")
        )
        mock_data_loader.return_value = [(loader_batch, None)]

        # the mocked trainer leaves two *different* checkpoints behind:
        # best_checkpoint holds zeroed weights, last_checkpoint the initial ones
        def make_states(model):
            last = model.state_dict()
            best = {k: torch.zeros_like(v) for k, v in last.items()}
            return {"best_checkpoint.pytorch": best, "last_checkpoint.pytorch": last}

        mock_trainer_instance = MagicMock()
        mock_trainer.return_value = mock_trainer_instance
        model_name = "test_model_export"
        _write_checkpoints(mock_trainer, tmp_path / model_name, make_states)

        dataset_dir = tmp_path / "dataset"
        (dataset_dir / "train").mkdir(parents=True)
        (dataset_dir / "val").mkdir()

        with (
            patch("panseg.functionals.training.train.PATH_PANSEG_MODELS", tmp_path),
            patch("panseg.core.zoo.PATH_PANSEG_MODELS", tmp_path),
        ):
            unet_training(
                dataset_dir=str(dataset_dir),
                model_name=model_name,
                in_channels=1,
                out_channels=1,
                feature_maps=(16, 16),
                patch_size=(1, 64, 64),
                max_num_iters=100,
                dimensionality="2D",
                sparse=False,
                device="cpu",
            )

        checkpoint_dir = tmp_path / model_name
        weights = checkpoint_dir / "best_checkpoint.pytorch"
        assert mock_model_desc.call_args.kwargs["weights"] == weights

        test_in = np.load(checkpoint_dir / "test_in.npy")
        test_out = np.load(checkpoint_dir / "test_out.npy")

        # test_in is stored as produced by the loader, un-normalized
        assert np.array_equal(test_in, loader_batch.squeeze(dim=-3).numpy())

        def _predict(state):
            model = UNet2D(
                in_channels=1,
                out_channels=1,
                f_maps=(16, 16),
                final_sigmoid=True,
                layer_order="bcr",
            )
            model.load_state_dict(state)
            model.eval()
            with torch.no_grad():
                out = model(zero_mean_unit_variance(torch.from_numpy(test_in)))
            return out.numpy()

        best_out = _predict(torch.load(weights, map_location="cpu"))
        last_out = _predict(
            torch.load(checkpoint_dir / "last_checkpoint.pytorch", map_location="cpu")
        )

        # test_out reproduces from the packaged (best) weights ...
        assert np.allclose(test_out, best_out, atol=1e-6)
        # ... and not from the last training state
        assert not np.allclose(test_out, last_out, atol=1e-3)

    @patch("panseg.functionals.training.train.UNetTrainer")
    @patch("panseg.functionals.training.train.create_datasets")
    @patch("panseg.functionals.training.train.create_model_config")
    def test_unet_training_with_existing_checkpoint_dir(
        self, mock_create_config, mock_create_datasets, mock_trainer
    ):
        """Test UNet training with existing checkpoint directory should fail."""
        # Mock the datasets with non-zero length
        mock_dataset = MagicMock()
        mock_dataset.__len__.return_value = 3  # Mock non-empty dataset
        mock_create_datasets.return_value = [mock_dataset]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary dataset directory
            dataset_dir = Path(temp_dir) / "dataset"
            dataset_dir.mkdir()
            (dataset_dir / "train").mkdir()
            (dataset_dir / "val").mkdir()

            # Create the checkpoint directory beforehand
            checkpoint_dir = Path(temp_dir) / "test_model"
            checkpoint_dir.mkdir(parents=True)

            # Patch PATH_PANSEG_MODELS to use temp directory
            with patch(
                "panseg.functionals.training.train.PATH_PANSEG_MODELS",
                Path(temp_dir),
            ):
                with pytest.raises(
                    AssertionError, match="Checkpoint dir .* already exists"
                ):
                    unet_training(
                        dataset_dir=str(dataset_dir),
                        model_name="test_model",
                        in_channels=1,
                        out_channels=2,
                        feature_maps=(16, 32),
                        patch_size=(64, 64, 64),
                        max_num_iters=100,
                        dimensionality="2D",
                        sparse=False,
                        device="cpu",
                    )

    @patch("panseg.functionals.training.train.test_model")
    @patch("panseg.functionals.training.train.isinstance")
    @patch("panseg.functionals.training.train.make_model_description")
    @patch("panseg.functionals.training.train.DataLoader")
    @patch("panseg.functionals.training.train.ConcatDataset")
    @patch("panseg.functionals.training.train.UNet2D")
    @patch("panseg.functionals.training.train.UNetTrainer")
    @patch("panseg.functionals.training.train.create_datasets")
    @patch("panseg.functionals.training.train.create_model_config")
    @patch("torch.cuda.device_count")
    @patch("torch.nn.DataParallel")
    @patch("panseg.functionals.training.train.Adam")
    @patch("panseg.functionals.training.train.ReduceLROnPlateau")
    @patch("panseg.functionals.training.train.find_batch_size")
    def test_unet_training_multi_gpu(
        self,
        mock_find_batch_size,
        mock_reduce_lr,
        mock_adam,
        mock_data_parallel,
        mock_device_count,
        mock_create_config,
        mock_create_datasets,
        mock_trainer,
        mock_unet,
        mock_concat,
        mock_data_loader,
        mock_description,
        mock_isinstance,
        mock_test_model,
        tmp_path,
    ):
        """Test UNet training with multiple GPUs."""

        # Mock DataParallel to avoid CUDA initialization
        mock_device_count.return_value = 2
        mock_parallel_model = MagicMock()
        mock_parallel_model.to.return_value = mock_parallel_model
        mock_data_parallel.return_value = mock_parallel_model

        mock_optimizer = MagicMock()
        mock_adam.return_value = mock_optimizer

        mock_scheduler = MagicMock()
        mock_reduce_lr.return_value = mock_scheduler

        mock_dataset = MagicMock()
        mock_dataset.__len__.return_value = 8  # Mock non-empty dataset
        mock_create_datasets.return_value = [mock_dataset]

        mock_trainer_instance = MagicMock()
        mock_trainer.return_value = mock_trainer_instance

        _write_checkpoints(
            mock_trainer,
            tmp_path / "test_model_multi_gpu",
            lambda model: {
                "best_checkpoint.pytorch": {},
                "last_checkpoint.pytorch": {},
            },
        )

        mock_data_loader.return_value = [
            (
                # torch.from_numpy(np.random.rand(1, 1, 64, 64)).type(torch.float32),
                mock_parallel_model,
                None,
            )
        ]

        mock_isinstance.return_value = False

        mock_find_batch_size.return_value = 1

        # Create a temporary dataset directory
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "train").mkdir()
        (dataset_dir / "val").mkdir()

        # Patch PATH_PANSEG_MODELS to use temp directory
        with patch("panseg.functionals.training.train.PATH_PANSEG_MODELS", tmp_path):
            with patch("panseg.core.zoo.PATH_PANSEG_MODELS", tmp_path):
                unet_training(
                    dataset_dir=str(dataset_dir),
                    model_name="test_model_multi_gpu",
                    in_channels=1,
                    out_channels=2,
                    feature_maps=(16, 32),
                    patch_size=(64, 64, 64),
                    max_num_iters=100,
                    dimensionality="2D",
                    sparse=False,
                    device="cuda",
                )

        # Verify that trainer was called
        mock_trainer_instance.train.assert_called_once()

        # Verify that DataParallel was called
        mock_data_parallel.assert_called_once()

        # Verify that Adam optimizer was called
        mock_adam.assert_called_once()

        # Verify that ReduceLROnPlateau scheduler was called
        mock_reduce_lr.assert_called_once()
