from module.DataTable import DataTable

from sklearn.model_selection import train_test_split
import numpy as np


class DataProcessor():
    
    def __init__(self, validation_fraction=None, test_fraction=None, seed=None, summary=None):
        if summary is None:
            self.validation_fraction = validation_fraction
            self.test_fraction = test_fraction
            self.seed = seed
        else:
            self.validation_fraction = summary.val_split
            self.test_fraction = summary.test_split
            self.seed = summary.seed

    def split_to_train_validate_test(self, data_table, train_idx=None, test_idx=None):
        
        if train_idx is None or test_idx is None:
            train_idx, test_idx = train_test_split(data_table.df.index,
                                                   test_size=self.test_fraction,
                                                   random_state=self.seed)

        train = np.asarray([train_idx]).T.flatten()
        test = np.asarray([test_idx]).T.flatten()
        
        train_and_validation_data = DataTable(data_table.df.loc[train])
        test_data = DataTable(data_table.df.loc[test], name="test")

        if self.validation_fraction > 0:
            train, validation = train_test_split(train_and_validation_data,
                                           test_size=self.validation_fraction,
                                           random_state=self.seed)
            train_data = DataTable(train, name="train")
            validation_data = DataTable(validation, name="validation")
        else:
            train_data = DataTable(train_and_validation_data, name="train")
            validation_data = None
  
        return train_data, validation_data, test_data, train_idx, test_idx

    def normalize(self, data_table, normalization_type, inverse=False,
                  data_ranges=None, norm_args=None, means=None, stds=None,
                  scaler=None):
        
        if normalization_type == "Custom":
            if data_ranges is None:
                print("Custom normalization selected, but no data ranges were provided!")
                exit(0)
            
            if not inverse:
                return data_table.normalize_in_range(rng=data_ranges)
            else:
                return data_table.inverse_normalize_in_range(rng=data_ranges)
        
        elif normalization_type in ["RobustScaler", "MinMaxScaler", "StandardScaler", "MaxAbsScaler"]:
            if scaler is None:
                data_table.setup_scaler(norm_type=normalization_type, scaler_args=norm_args)
                return data_table.normalize(inverse=inverse)
            else:
                return data_table.normalize(inverse=inverse, scaler=scaler)
        elif normalization_type == "CustomStandard":
            if means is None or stds is None:
                print("Custom standard normalization selected, but means or stds not provided!")
                exit(0)
            return data_table.custom_standard_normalize(means=means, stds=stds, inverse=inverse)
        elif normalization_type == "None":
            return data_table
        else:
            print("ERROR -- Normalization not implemented: ", normalization_type)
            exit(0)
