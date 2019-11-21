
from os import path, mkdir
from .error import SSModelExistsError

class Target:

    def __init__(self, name, params, experiment_name, target_dir_path):
        self.name = name
        self.params = params
        self.path = target_dir_path
        self.experiment = experiment_name
        self.models = {}


    def add_model(self, model):
        if model.name in self.models:
            raise SSModelExistsError("Adding model to target",
                                "Model name: " + model.name + " already exists in target: " + self.name)
        else:
            self.models[model.name] = model

    def __str__(self):
        target_str = "\n   " + self.name + "\n"
        for model in self.models.values():
            target_str += str(model)
        target_str += "\n"
        return target_str

    def __getitem__(self, model_name):
        return self.models[model_name]

    def __len__(self):
        return len(self.models.values())
