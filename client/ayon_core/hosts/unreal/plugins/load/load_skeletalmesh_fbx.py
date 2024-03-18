# -*- coding: utf-8 -*-
"""Load Skeletal Meshes form FBX."""
import os

from ayon_core.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from ayon_core.hosts.unreal.api import plugin
from ayon_core.hosts.unreal.api.pipeline import (
    AYON_ASSET_DIR,
    create_container,
    imprint,
)
import unreal  # noqa


class SkeletalMeshFBXLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["rig", "skeletalMesh"]
    label = "Import FBX Skeletal Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    root = AYON_ASSET_DIR

    @staticmethod
    def get_task(filename, asset_dir, asset_name, replace):
        task = unreal.AssetImportTask()
        options = unreal.FbxImportUI()

        task.set_editor_property('filename', filename)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', replace)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        options.set_editor_property(
            'automated_import_should_detect_type', False)
        options.set_editor_property('import_as_skeletal', True)
        options.set_editor_property('import_animations', False)
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('skeleton', None)
        options.set_editor_property('create_physics_asset', False)

        options.set_editor_property(
            'mesh_type_to_import',
            unreal.FBXImportType.FBXIT_SKELETAL_MESH)

        options.skeletal_mesh_import_data.set_editor_property(
            'import_content_type',
            unreal.FBXImportContentType.FBXICT_ALL)

        options.skeletal_mesh_import_data.set_editor_property(
            'normal_import_method',
            unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)

        task.options = options

        return task

    def import_and_containerize(
        self, filepath, asset_dir, asset_name, container_name
    ):
        unreal.EditorAssetLibrary.make_directory(asset_dir)

        task = self.get_task(
            filepath, asset_dir, asset_name, False)

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        # Create Asset Container
        create_container(container=container_name, path=asset_dir)

    def imprint(
        self,
        folder_path,
        asset_dir,
        container_name,
        asset_name,
        representation,
        product_type
    ):
        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "folder_path": folder_path,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": representation["id"],
            "parent": representation["versionId"],
            "product_type": product_type,
            # TODO these should be probably removed
            "asset": folder_path,
            "family": product_type,
        }
        imprint(f"{asset_dir}/{container_name}", data)

    def load(self, context, name, namespace, options):
        """Load and containerise representation into Content Browser.

        Args:
            context (dict): application context
            name (str): Product name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            data (dict): Those would be data to be imprinted.

        Returns:
            list(str): list of container content
        """
        # Create directory for asset and Ayon container
        folder_name = context["folder"]["name"]
        product_type = context["product"]["productType"]
        suffix = "_CON"
        asset_name = f"{folder_name}_{name}" if folder_name else f"{name}"
        version_entity = context["version"]
        # Check if version is hero version and use different name
        version = version_entity["version"]
        if version < 0:
            name_version = f"{name}_hero"
        else:
            name_version = f"{name}_v{version:03d}"

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{self.root}/{folder_name}/{name_version}", suffix=""
        )

        container_name += suffix

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            path = self.filepath_from_context(context)

            self.import_and_containerize(
                path, asset_dir, asset_name, container_name)

        self.imprint(
            folder_name,
            asset_dir,
            container_name,
            asset_name,
            context["representation"],
            product_type
        )

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, context):
        folder_path = context["folder"]["path"]
        folder_name = context["folder"]["name"]
        product_name = context["product"]["name"]
        product_type = context["product"]["productType"]
        version = context["version"]["version"]
        repre_entity = context["representation"]

        # Create directory for asset and Ayon container
        suffix = "_CON"
        asset_name = product_name
        if folder_name:
            asset_name = f"{folder_name}_{product_name}"
        # Check if version is hero version and use different name
        if version < 0:
            name_version = f"{product_name}_hero"
        else:
            name_version = f"{product_name}_v{version:03d}"
        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{self.root}/{folder_name}/{name_version}", suffix="")

        container_name += suffix

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            path = get_representation_path(repre_entity)

            self.import_and_containerize(
                path, asset_dir, asset_name, container_name)

        self.imprint(
            folder_path, 
            asset_dir,
            container_name,
            asset_name,
            repre_entity,
            product_type
        )

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        unreal.EditorAssetLibrary.delete_directory(path)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            parent_path, recursive=False
        )

        if len(asset_content) == 0:
            unreal.EditorAssetLibrary.delete_directory(parent_path)
