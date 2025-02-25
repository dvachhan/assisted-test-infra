from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from assisted_service_client import models

from assisted_test_infra.test_infra import BaseEntityConfig
from assisted_test_infra.test_infra.helper_classes.nodes import Nodes
from service_client import InventoryClient, log


class Entity(ABC):
    def __init__(self, api_client: InventoryClient, config: BaseEntityConfig, nodes: Optional[Nodes] = None):
        self._config = config
        self.api_client = api_client
        self.nodes: Nodes = nodes
        self._create() if not self.id else self.update_existing()

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    def _entity_class_name(self):
        return self.__class__.__name__.lower()

    @abstractmethod
    def _create(self) -> str:
        pass

    @abstractmethod
    def update_existing(self) -> str:
        pass

    @abstractmethod
    def download_image(self, iso_download_path: str = None) -> Path:
        pass

    def update_config(self, **kwargs):
        """
        Note that kwargs can contain values for overriding BaseClusterConfig arguments.
        The name (key) of each argument must match to one of the BaseEntityConfig arguments.
        If key doesn't exists in config - KeyError exception is raised
        """
        log.info(f"Updating {self._entity_class_name} configurations to {kwargs}")

        for k, v in kwargs.items():
            if not hasattr(self._config, k):
                raise KeyError(f"The key {k} is not present in {self._config.__class__.__name__}")
            setattr(self._config, k, v)

    def prepare_for_installation(self, **kwargs):
        self.update_config(**kwargs)
        log.info(
            f"Preparing for installation with {self._entity_class_name} configurations: "
            f"{self._entity_class_name}_config={self._config}"
        )

        self.nodes.controller.log_configuration()

        if self._config.download_image:
            self.download_image()

        self.nodes.notify_iso_ready()
        self.nodes.start_all(check_ips=not (self._config.is_static_ip and self._config.is_ipv6))
        self.wait_until_hosts_are_discovered(allow_insufficient=True)

    @abstractmethod
    def get_details(self) -> Union[models.infra_env.InfraEnv, models.cluster.Cluster]:
        pass

    @abstractmethod
    def wait_until_hosts_are_discovered(self, nodes_count: int = None, allow_insufficient=False):
        pass
