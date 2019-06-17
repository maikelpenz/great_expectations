import os

import pandas as pd
import json
import logging
import uuid
import errno

from six import string_types

import great_expectations.dataset as dataset
from great_expectations.data_context import DataContext

logger = logging.getLogger(__name__)


def _convert_to_dataset_class(df, dataset_class, expectations_config=None, profiler=None):
    """
    Convert a (pandas) dataframe to a great_expectations dataset, with (optional) expectations_config
    """
    if expectations_config is not None:
        # Create a dataset of the new class type, and manually initialize expectations according to the provided configuration
        new_df = dataset_class.from_dataset(df)
        new_df._initialize_expectations(expectations_config)
    else:
        # Instantiate the new Dataset with default expectations
        new_df = dataset_class.from_dataset(df)
        if profiler is not None:
            new_df.profile(profiler)

    return new_df


def read_csv(
    filename,
    dataset_class=dataset.pandas_dataset.PandasDataset,
    expectations_config=None,
    profiler=None,
    *args, **kwargs
):
    df = pd.read_csv(filename, *args, **kwargs)
    df = _convert_to_dataset_class(
        df, dataset_class, expectations_config, profiler)
    return df


def read_json(
    filename,
    dataset_class=dataset.pandas_dataset.PandasDataset,
    expectations_config=None,
    accessor_func=None,
    profiler=None,
    *args, **kwargs
):
    if accessor_func != None:
        json_obj = json.load(open(filename, 'rb'))
        json_obj = accessor_func(json_obj)
        df = pd.read_json(json.dumps(json_obj), *args, **kwargs)

    else:
        df = pd.read_json(filename, *args, **kwargs)

    df = _convert_to_dataset_class(
        df, dataset_class, expectations_config, profiler)
    return df


def read_excel(
    filename,
    dataset_class=dataset.pandas_dataset.PandasDataset,
    expectations_config=None,
    profiler=None,
    *args, **kwargs
):
    """Read a file using Pandas read_excel and return a great_expectations dataset.

    Args:
        filename (string): path to file to read
        dataset_class (Dataset class): class to which to convert resulting Pandas df
        expectations_config (string): path to great_expectations config file

    Returns:
        great_expectations dataset or ordered dict of great_expectations datasets,
        if multiple worksheets are imported
    """
    df = pd.read_excel(filename, *args, **kwargs)
    if isinstance(df, dict):
        for key in df:
            df[key] = _convert_to_dataset_class(
                df[key], dataset_class, expectations_config, profiler)
    else:
        df = _convert_to_dataset_class(
            df, dataset_class, expectations_config, profiler)
    return df


def read_table(
    filename,
    dataset_class=dataset.pandas_dataset.PandasDataset,
    expectations_config=None,
    profiler=None,
    *args, **kwargs
):
    """Read a file using Pandas read_table and return a great_expectations dataset.

    Args:
        filename (string): path to file to read
        dataset_class (Dataset class): class to which to convert resulting Pandas df
        expectations_config (string): path to great_expectations config file

    Returns:
        great_expectations dataset
    """
    df = pd.read_table(filename, *args, **kwargs)
    df = _convert_to_dataset_class(
        df, dataset_class, expectations_config, profiler)
    return df


def read_parquet(
    filename,
    dataset_class=dataset.pandas_dataset.PandasDataset,
    expectations_config=None,
    profiler=None,
    *args, **kwargs
):
    """Read a file using Pandas read_parquet and return a great_expectations dataset.

    Args:
        filename (string): path to file to read
        dataset_class (Dataset class): class to which to convert resulting Pandas df
        expectations_config (string): path to great_expectations config file

    Returns:
        great_expectations dataset
    """
    df = pd.read_parquet(filename, *args, **kwargs)
    df = _convert_to_dataset_class(
        df, dataset_class, expectations_config, profiler)
    return df


def from_pandas(pandas_df,
                dataset_class=dataset.pandas_dataset.PandasDataset,
                expectations_config=None,
                profiler=None
                ):
    """Read a Pandas data frame and return a great_expectations dataset.

    Args:
        pandas_df (Pandas df): Pandas data frame
        dataset_class (Dataset class) = dataset.pandas_dataset.PandasDataset:
            class to which to convert resulting Pandas df
        expectations_config (string) = None: path to great_expectations config file
        profiler (profiler class) = None: The profiler that should 
            be run on the dataset to establish a baseline expectation suite.

    Returns:
        great_expectations dataset
    """
    return _convert_to_dataset_class(
        pandas_df,
        dataset_class,
        expectations_config,
        profiler
    )


def validate(data_asset, expectations_config=None, data_asset_name=None, data_context=None, data_asset_type=None, *args, **kwargs):
    """Validate the provided data asset using the provided config"""
    if expectations_config is None and data_context is None:
        raise ValueError(
            "Either an expectations config or a DataContext is required for validation.")

    if expectations_config is None:
        logger.info("Using expectations config from DataContext.")
        # Allow data_context to be a string, and try loading it from path in that case
        if isinstance(data_context, string_types):
            data_context = DataContext(data_context)                
        expectations_config = data_context.get_expectations(data_asset_name)
    else:
        if data_asset_name in expectations_config:
            logger.info("Using expectations config with name %s" %
                        expectations_config["data_asset_name"])
        else:
            logger.info("Using expectations config with no data_asset_name")

    # If the object is already a Dataset type, then this is purely a convenience method
    # and no conversion is needed
    if isinstance(data_asset, dataset.Dataset) and data_asset_type is None:
        return data_asset.validate(expectations_config=expectations_config, data_context=data_context, *args, **kwargs)
    elif data_asset_type is None:
        # Guess the GE data_asset_type based on the type of the data_asset
        if isinstance(data_asset, pd.DataFrame):
            data_asset_type = dataset.PandasDataset
        # Add other data_asset_type conditions here as needed

    # Otherwise, we will convert for the user to a subclass of the
    # existing class to enable new expectations, but only for datasets
    if not isinstance(data_asset, (dataset.Dataset, pd.DataFrame)):
        raise ValueError(
            "The validate util method only supports dataset validations, including custom subclasses. For other data asset types, use the object's own validate method.")

    if not issubclass(type(data_asset), data_asset_type):
        if isinstance(data_asset, (pd.DataFrame)) and issubclass(data_asset_type, dataset.PandasDataset):
            pass  # This is a special type of allowed coercion
        else:
            raise ValueError(
                "The validate util method only supports validation for subtypes of the provided data_asset_type.")

    data_asset_ = _convert_to_dataset_class(
        data_asset, data_asset_type, expectations_config)
    return data_asset_.validate(*args, data_context=data_context, **kwargs)


class DotDict(dict):
    """dot.notation access to dictionary attributes"""

    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __dir__(self):
        return self.keys()
