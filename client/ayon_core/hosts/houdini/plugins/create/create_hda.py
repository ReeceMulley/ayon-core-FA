# -*- coding: utf-8 -*-
"""Creator plugin for creating publishable Houdini Digital Assets."""
import ayon_api
import getpass
from ayon_core.pipeline import CreatorError
from ayon_core.hosts.houdini.api import plugin
from ayon_core.lib import BoolDef
import hou
from ayon_core.resources import get_ayon_icon_filepath


class CreateHDA(plugin.HoudiniCreator):
    """Publish Houdini Digital Asset file."""

    identifier = "io.openpype.creators.houdini.hda"
    label = "Houdini Digital Asset (Hda)"
    product_type = "hda"
    icon = "gears"
    maintain_selection = False

    def _check_existing(self, folder_path, product_name):
        # type: (str, str) -> bool
        """Check if existing product name versions already exists."""
        # Get all products of the current folder
        project_name = self.project_name
        folder_entity = ayon_api.get_folder_by_path(
            project_name, folder_path, fields={"id"}
        )
        product_entities = ayon_api.get_products(
            project_name, folder_ids={folder_entity["id"]}, fields={"name"}
        )
        existing_product_names_low = {
            product_entity["name"].lower()
            for product_entity in product_entities
        }
        return product_name.lower() in existing_product_names_low

    def create_instance_node(
        self,
        folder_path,
        node_name,
        parent,
        node_type="geometry",
        pre_create_data=None
    ):
        if pre_create_data is None:
            pre_create_data = {}

        if self.selected_nodes:
            # if we have `use selection` enabled, and we have some
            # selected nodes ...
            if self.selected_nodes[0].type().name() == "subnet":
                to_hda = self.selected_nodes[0]
                to_hda.setName("{}_subnet".format(node_name), unique_name=True)
            else:
                parent_node = self.selected_nodes[0].parent()
                subnet = parent_node.collapseIntoSubnet(
                    self.selected_nodes,
                    subnet_name="{}_subnet".format(node_name))
                subnet.moveToGoodPosition()
                to_hda = subnet
        else:
            # Use Obj as the default path
            parent_node = hou.node("/obj")
            # Find and return the NetworkEditor pane tab with the minimum index
            pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if isinstance(pane, hou.NetworkEditor):
                # Use the NetworkEditor pane path as the parent path.
                parent_node = pane.pwd()

            to_hda = parent_node.createNode(
                "subnet", node_name="{}_subnet".format(node_name))
        if not to_hda.type().definition():
            # if node type has not its definition, it is not user
            # created hda. We test if hda can be created from the node.
            if not to_hda.canCreateDigitalAsset():
                raise CreatorError(
                    "cannot create hda from node {}".format(to_hda))

            hda_node = to_hda.createDigitalAsset(
                name=node_name,
                hda_file_name="$HIP/{}.hda".format(node_name),
                ignore_external_references=True
            )
            hda_node.layoutChildren()
        elif self._check_existing(folder_path, node_name):
            raise CreatorError(
                ("product {} is already published with different HDA"
                 "definition.").format(node_name))
        else:
            hda_node = to_hda

        # If user tries to create the same HDA instance more than
        # once, then all of them will have the same product name and
        # point to the same hda_file_name. But, their node names will
        # be incremented.
        hda_node.setName(node_name, unique_name=True)
        self.customize_node_look(hda_node)

        # Set Custom settings.
        hda_def = hda_node.type().definition()

        if pre_create_data.get("use_ayon_icon"):
            hda_def.setIcon(get_ayon_icon_filepath())

        if pre_create_data.get("set_user"):
            hda_def.setUserInfo(getpass.getuser())

        if pre_create_data.get("use_project"):
            tool_name = hou.shelves.defaultToolName(
                hda_def.nodeTypeCategory().name(), hda_def.nodeTypeName())
            hou.shelves.tool(tool_name).setToolLocations(
                ("AYON/{}".format(self.project_name),))

        return hda_node

    def create(self, product_name, instance_data, pre_create_data):
        instance_data.pop("active", None)

        return super(CreateHDA, self).create(
            product_name,
            instance_data,
            pre_create_data)

    def get_network_categories(self):
        # Houdini allows creating sub-network nodes inside
        # these categories.
        # Therefore this plugin can work in these categories.
        return [
            hou.chopNodeTypeCategory(),
            hou.cop2NodeTypeCategory(),
            hou.dopNodeTypeCategory(),
            hou.ropNodeTypeCategory(),
            hou.lopNodeTypeCategory(),
            hou.objNodeTypeCategory(),
            hou.sopNodeTypeCategory(),
            hou.topNodeTypeCategory(),
            hou.vopNodeTypeCategory()
        ]

    def get_pre_create_attr_defs(self):
        attrs = super(CreateHDA, self).get_pre_create_attr_defs()
        return attrs + [
            BoolDef("use_ayon_icon",
                    tooltip="Use Ayon icon for the digital asset.",
                    default=False,
                    label="Use AYON Icon"),
            BoolDef("set_user",
                    tooltip="Set current user as the author of the HDA",
                    default=False,
                    label="Set Current User"),
            BoolDef("use_project",
                    tooltip="Use project name as tab submenu path",
                    default=True,
                    label="Use Project as menu entry"),
        ]
