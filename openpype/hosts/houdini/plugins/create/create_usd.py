# -*- coding: utf-8 -*-
"""Creator plugin for creating USDs."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateUSD(plugin.HoudiniCreator):
    """Universal Scene Description"""
    identifier = "io.openpype.creators.houdini.usd"
    label = "USD (experimental)"
    family = "usd"
    icon = "gears"
    enabled = False

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "usd"})

        instance = super(CreateUSD, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "lopoutput": "$HIP/pyblish/{}.usd".format(subset_name),
            "enableoutputprocessor_simplerelativepaths": False,
        }

        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = [
            "fileperframe",
            # Lock some Avalon attributes
            "family",
            "id",
        ]
        for name in to_lock:
            parm = instance_node.parm(name)
            parm.lock(True)
