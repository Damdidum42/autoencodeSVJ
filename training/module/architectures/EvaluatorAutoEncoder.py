import glob, os
import tensorflow as tf
import keras
from keras.models import model_from_json
from sklearn.metrics import roc_auc_score
from sklearn.metrics import roc_curve
import pandas as pd
import pickle

from module.architectures.DenseTiedLayer import DenseTiedLayer


class EvaluatorAutoEncoder:
    def __init__(self, input_path, custom_objects):
        
        self.custom_objects = custom_objects
        
        self.signal_dict = {}
        for path in glob.glob(input_path):
            key = path.split("/")[-3]
            self.signal_dict[key] = path
    
    def get_weights(self, summary):
        model = self.__load_model(summary)
        return model.get_weights()

    
    def get_qcd_data(self, summary, data_processor, data_loader, normalize=False, test_data_only=True):
        
        (data, _, _, _) = data_loader.load_all_data(globstring=summary.qcd_path, name="QCD")
        if test_data_only:
            (_, _, data) = data_processor.split_to_train_validate_test(data)

        if normalize:
            data = data_processor.normalize(data_table=data,
                                            normalization_type=summary.norm_type,
                                            norm_args=summary.norm_args)
        
        return data
    
    def get_signal_data(self, name, path, summary, data_processor, data_loader, normalize=False, scaler=None, test_data_only=True):
        
        (data, _, _, _) = data_loader.load_all_data(globstring=path, name=name)
        
        if test_data_only:
            (_, _, data) = data_processor.split_to_train_validate_test(data)
        
        if normalize:
            data = data_processor.normalize(data_table=data,
                                            normalization_type=summary.norm_type,
                                            norm_args=summary.norm_args,
                                            scaler=scaler)
        
        return data
        
    def get_reconstruction(self, input_data, summary, data_processor, scaler):
    
        input_data_normed = data_processor.normalize(data_table=input_data,
                                                     normalization_type=summary.norm_type,
                                                     norm_args=summary.norm_args,
                                                     scaler=scaler)

        model = self.__load_model(summary)
        
        reconstructed = pd.DataFrame(model.predict(input_data_normed.data),
                                     columns=input_data_normed.columns,
                                     index=input_data_normed.index,
                                     dtype="float64")

        descaler = input_data.scaler if scaler is None else scaler

        reconstructed_denormed = data_processor.normalize(data_table=reconstructed,
                                                          normalization_type=summary.norm_type,
                                                          norm_args=summary.norm_args,
                                                          scaler=descaler,
                                                          inverse=True)
        
        return reconstructed_denormed
        
    def get_error(self, input_data, summary, data_processor, scaler):
        recon = self.get_reconstruction(input_data, summary, data_processor, scaler)
        
        print("Calculating error using loss: ", summary.loss)
        
        func = getattr(keras.losses, summary.loss)
        losses = keras.backend.eval(func(input_data.data, recon))
        
        return losses.tolist()
        
    def get_aucs(self, summary, AUCs_path, filename, data_processor, data_loader):
        
        auc_path = AUCs_path + "/" + filename
    
        if os.path.exists(auc_path):
            print("File :", auc_path, "\talready exists. Skipping...")
            return None
        else:
            print("Preparing: ", auc_path)
    
        tf.compat.v1.reset_default_graph()
    
        model = self.__load_model(summary)
    
        print("using summary: ", summary)
        print("AUCs path:", auc_path)
        print("filename: ", filename)
    
        aucs = self.__get_aucs(summary=summary,
                               data_processor=data_processor,
                               data_loader=data_loader,
                               model=model,
                               loss_function=summary.loss
                               )
        
        print("aucs: ", aucs)
        
        append = False
        write_header = True
        
        return (aucs, auc_path, append, write_header)

    def draw_roc_curves(self, summary, data_processor, data_loader, ax, colors, signals, test_key="qcd", **kwargs):

        normed = {
            test_key: self.get_qcd_data(summary, data_processor, data_loader, normalize=True, test_data_only=True)
        }

        for name, path in signals.items():
            normed[name] = self.get_signal_data(name, path, summary, data_processor, data_loader,
                                                normalize=True, scaler = normed[test_key].scaler)
        
        errors = {}
        model = self.__load_model(summary)

        for key, data in normed.items():
            recon = pd.DataFrame(model.predict(data.data), columns=data.columns, index=data.index, dtype="float64")
            func = getattr(keras.losses, summary.loss)
            losses = keras.backend.eval(func(data.data, recon))
            errors[key] = losses.tolist()

        signals_errors = {}
        
        for signal in signals:
            signals_errors[signal] = errors[signal]

        qcd_errors = errors[test_key]

        self.__roc_auc_plot(qcd_errors, signals_errors, ax, colors)

    def __roc_auc_plot(self, background_errors, signal_errs, ax, colors):
    
        background_labels = [0] * len(background_errors)
        
        i = 0
        
        for name, signal_err in signal_errs.items():
            pred = signal_err + background_errors
            true = [1] * len(signal_err)
            true = true + background_labels
            
            roc = roc_curve(y_true=true, y_score=pred)
            auc = roc_auc_score(y_true=true, y_score=pred)
            
            ax.plot(roc[0], roc[1], "-", c=colors[i % len(colors)], label='{}, AUC {:.4f}'.format(name, auc))

            i += 1
        
    def __load_model(self, summary):
    
        model_path = summary.training_output_path + ".h5"

        try:
            print("Trying to read model with keras load_model")
            model = tf.keras.models.load_model(model_path, custom_objects=self.custom_objects)
        except:
            print("Failed reading model with keras load_model")
            model_path = model_path.replace(".h5", ".pkl")
            try:
                print("Trying to read model with model_from_json")
                model_file = open(model_path, 'rb')
                model = model_from_json(pickle.load(model_file), custom_objects=self.custom_objects)
            except IOError:
                print("Failed reading model with model_from_json")
                return None

        model.summary()

        # config = model.get_config()
        #
        # with keras.utils.custom_object_scope(self.custom_objects):
        #     model = keras.Model.from_config(config)
    
        model.load_weights(summary.training_output_path + "_weights.h5")
        
        return model

    def __get_aucs(self, summary, data_processor, data_loader, model, loss_function, test_key='qcd'):
        
        normed = {
            test_key: self.get_qcd_data(summary, data_processor, data_loader, normalize=True, test_data_only=True)
        }
    
        background_path_components = summary.qcd_path.split("/")
        efp_base_path = None
        
        for element in background_path_components:
            if "base" in element:
                efp_base_path = element
                break
        
    
        for name, path in self.signal_dict.items():
            if name == test_key: continue

            path_components = path.split("/")
            new_path = ""
            
            for element in path_components:
                if "base" in element:
                    new_path += efp_base_path
                else:
                    new_path += element
                new_path += "/"
            
            normed[name] = self.get_signal_data(name=name, path=new_path,
                                                summary=summary,
                                                data_processor=data_processor, data_loader= data_loader,
                                                normalize=True, scaler=normed[test_key].scaler)

        errors = {}
    
        for key, data in normed.items():
            recon = pd.DataFrame(model.predict(data.data), columns=data.columns, index=data.index, dtype="float64")
            func = getattr(keras.losses, loss_function)
            losses = keras.backend.eval(func(data.data, recon))
            errors[key] = losses.tolist()
    
        background_errors = errors[test_key]
        background_labels = [0] * len(background_errors)
    
        aucs = []
        for name, signal_err in errors.items():
            if name == test_key: continue
        
            pred = signal_err + background_errors
            true = [1] * len(signal_err)
            true = true + background_labels
        
            auc = roc_auc_score(y_true=true, y_score=pred)
        
            signal_components = name.split("_")
            mass_index = [i for i, s in enumerate(signal_components) if 'GeV' in s][0]
            mass = int(signal_components[mass_index].strip("GeV"))
            rinv = float(signal_components[mass_index + 1])
        
            aucs.append({"mass": mass, "rinv": rinv, "auc": auc})
    
        return aucs