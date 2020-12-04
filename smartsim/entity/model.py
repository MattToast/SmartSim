from .files import EntityFiles
from ..error import SSConfigError
from .entity import SmartSimEntity
from ..utils.helpers import expand_exe_path


class Model(SmartSimEntity):
    def __init__(self, name, params, path, run_settings):
        """Initialize a model entity within Smartsim

        :param name: name of the model
        :type name: str
        :param params: model parameters for writing into configuration files.
        :type params: dict
        :param path: path to output, error, and configuration files
        :type path: str
        :param run_settings: launcher settings specified in the experiment
        :type run_settings: dict
        """
        super().__init__(name, path, "model", run_settings)
        if not isinstance(params, dict):
            raise TypeError(
                "Model initialization argument 'params' must be of type dict"
            )
        self.params = params
        self.incoming_entities = []
        self._key_prefixing_enabled = False
        self.files = None
        self._init_run_settings()

    def _init_run_settings(self):
        """Initialize the run_settings for the model"""

        # set the path to the error, output, and runtime dir
        self.set_path(self.path)
        # expand the executable path
        self.run_settings["executable"] = self._expand_entity_exe()

    def register_incoming_entity(self, incoming_entity, receiving_client_type):
        """Register future communication between entities.

        Registers the named data sources that this entity
        has access to by storing the key_prefix associated
        with that entity

        Only python clients can have multiple incoming connections

        :param incoming_entity: The entity that data will be received from
        :param incoming_entity: SmartSimEntity
        :param receiving_client_type: The language of the SmartSim client used by
                                      this object. Can be cpp, fortran, python
        :param receiving_client_type: str
        """
        # Update list as clients are developed
        multiple_conn_supported = receiving_client_type in ["python"]
        if not multiple_conn_supported and self.incoming_entities:
            raise SSConfigError(
                f"Receiving client of type '{receiving_client_type}'"
                + " does not support multiple incoming connections"
            )
        if incoming_entity.name in [
            in_entity.name for in_entity in self.incoming_entities
        ]:
            raise SSConfigError(
                f"'{incoming_entity.name}' has already"
                + "been registered as an incoming entity"
            )

        self.incoming_entities.append(incoming_entity)

    def enable_key_prefixing(self):
        """If called, the entity will prefix its keys with its own model name"""
        self._key_prefixing_enabled = True

    def disable_key_prefixing(self):
        """If called, the entity will not prefix its keys with its own model name"""
        self._key_prefixing_enabled = False

    def query_key_prefixing(self):
        """Inquire as to whether this entity will prefix its keys with its name"""
        return self._key_prefixing_enabled

    def attach_generator_files(self, to_copy=[], to_symlink=[], to_configure=[]):
        """Attach files to an entity for generation

           Attach files needed for the entity that, upon generation,
           will be located in the path of the entity.

           During generation files "to_copy" are just copied into
           the path of the entity, and files "to_symlink" are
           symlinked into the path of the entity.

           Files "to_configure" are text based model input files where
           parameters for the model are set. Note that only models
           support the "to_configure" field. These files must have
           fields tagged that correspond to the values the user
           would like to change. The tag is settable but defaults
           to a semicolon e.g. THERMO = ;10;

        :param to_copy: files to copy, defaults to []
        :type to_copy: list, optional
        :param to_symlink: files to symlink, defaults to []
        :type to_symlink: list, optional
        :param to_configure: input files with tagged parameters, defaults to []
        :type to_configure: list, optional
        """
        self.files = EntityFiles(to_configure, to_copy, to_symlink)

    def _expand_entity_exe(self):
        """Run at initialization, this function finds and expands
           the executable for the entity.

        :param run_settings: dictionary of run_settings
        :type run_settings: dict
        """
        try:
            exe = self.run_settings["executable"]
            full_exe = expand_exe_path(exe)
            return full_exe
        except KeyError:
            raise SSConfigError(
                f"User did not provide an executable in the run settings for {self.name}"
            )
        except SSConfigError as e:
            raise SSConfigError(
                f"Failed to create entity, bad executable argument in run settings"
            ) from e

    def get_param_value(self, param):
        """Get a value of a model parameter

        :param param: parameter name
        :type param: str
        :return: value of the model parameter
        :rtype: str
        """
        return self.params[param]

    def __eq__(self, other):
        if self.name == other.name:
            return True
        return False

    def __repr__(self):
        return self.name

    def __str__(self):
        entity_str = "Name: " + self.name + "\n"
        entity_str += "Type: " + self.type + "\n"
        entity_str += "run_settings = {\n"
        for param, value in self.run_settings.items():
            param = '"' + param + '"'
            if isinstance(value, str):
                value = '"' + value + '"'
            entity_str += " ".join((" ", str(param), ":", str(value), "\n"))
        entity_str += "}"
        return entity_str
