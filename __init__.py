# ManuelbastioniLAB - Copyright (C) 2015-2018 Manuel Bastioni
# Official site: www.manuelbastioni.com
# MB-Lab fork website : https://github.com/animate1978/MB-Lab
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

import time
import json
import os

import bpy
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import facerig
from . import humanoid, animationengine, proxyengine
from . import utils

logger = logging.getLogger(__name__)

bl_info = {
    "name": "MB-Lab",
    "author": "Manuel Bastioni",
    "version": (1, 7, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Tools > MB-Lab",
    "description": "A complete lab for character creation",
    "warning": "",
    'wiki_url': "https://github.com/animate1978/MB-Lab/wiki",
    'tracker_url': 'https://github.com/animate1978/MB-Lab/issues',
    "category": "Characters"
}


mblab_humanoid = humanoid.Humanoid(bl_info["version"])
mblab_retarget = animationengine.RetargetEngine()
mblab_shapekeys = animationengine.ExpressionEngineShapeK()
mblab_proxy = proxyengine.ProxyEngine()

gui_status = "NEW_SESSION"
gui_err_msg = ""
gui_active_panel = None
gui_active_panel_fin = None


def start_lab_session():

    global mblab_humanoid
    global gui_status, gui_err_msg

    logger.info("Start_the lab session...")
    scn = bpy.context.scene
    character_identifier = scn.mblab_character_name
    rigging_type = "base"
    if scn.mblab_use_ik:
        rigging_type = "ik"
    if scn.mblab_use_muscle:
        rigging_type = "muscle"
    if scn.mblab_use_muscle and scn.mblab_use_ik:
        rigging_type = "muscle_ik"

    lib_filepath = algorithms.get_blendlibrary_path()

    obj = None
    is_existing = False
    is_obj = algorithms.looking_for_humanoid_obj()

    if is_obj[0] == "ERROR":
        gui_status = "ERROR_SESSION"
        gui_err_msg = is_obj[1]
        return

    if is_obj[0] == "NO_OBJ":
        base_model_name = mblab_humanoid.characters_config[character_identifier]["template_model"]
        obj = algorithms.import_object_from_lib(lib_filepath, base_model_name, character_identifier)
        obj["manuellab_vers"] = bl_info["version"]
        obj["manuellab_id"] = character_identifier
        obj["manuellab_rig"] = rigging_type

    if is_obj[0] == "FOUND":
        obj = algorithms.get_object_by_name(is_obj[1])
        character_identifier = obj["manuellab_id"]
        rigging_type = obj["manuellab_rig"]
        is_existing = True

    if not obj:
        logger.critical("Init failed...")
        gui_status = "ERROR_SESSION"
        gui_err_msg = "Init failed. Check the log file"
    else:
        mblab_humanoid.init_database(obj, character_identifier, rigging_type)
        if mblab_humanoid.has_data:
            gui_status = "ACTIVE_SESSION"

            if scn.mblab_use_cycles or scn.mblab_use_eevee:
                if scn.mblab_use_cycles:
                    scn.render.engine = 'CYCLES'
                else:
                    scn.render.engine = 'BLENDER_EEVEE'
                if scn.mblab_use_lamps:
                    algorithms.import_object_from_lib(lib_filepath, "Lamp_back_bottom")
                    algorithms.import_object_from_lib(lib_filepath, "Lamp_back_up")
                    algorithms.import_object_from_lib(lib_filepath, "Lamp_left")
                    algorithms.import_object_from_lib(lib_filepath, "Lamp_right")
                    #algorithms.append_object_from_library(lib_filepath, [], "Lamp_")
            else:
                scn.render.engine = 'BLENDER_WORKBENCH'

            logger.info("Rendering engine now is %s", scn.render.engine)
            init_morphing_props(mblab_humanoid)
            init_categories_props(mblab_humanoid)
            init_measures_props(mblab_humanoid)
            init_restposes_props(mblab_humanoid)
            init_presets_props(mblab_humanoid)
            init_ethnic_props(mblab_humanoid)
            init_metaparameters_props(mblab_humanoid)
            init_material_parameters_props(mblab_humanoid)
            mblab_humanoid.update_materials()

            if is_existing:
                logger.info("Re-init the character %s", obj.name)
                mblab_humanoid.store_mesh_in_cache()
                mblab_humanoid.reset_mesh()
                mblab_humanoid.recover_prop_values_from_obj_attr()
                mblab_humanoid.restore_mesh_from_cache()
            else:
                mblab_humanoid.reset_mesh()
                mblab_humanoid.update_character(mode="update_all")

            algorithms.deselect_all_objects()


@persistent
def check_manuelbastionilab_session(dummy):
    global mblab_humanoid
    global gui_status, gui_err_msg
    scn = bpy.context.scene
    if mblab_humanoid:
        # init_femaleposes_props()
        # init_maleposes_props()
        gui_status = "NEW_SESSION"
        is_obj = algorithms.looking_for_humanoid_obj()
        if is_obj[0] == "FOUND":
            #gui_status = "RECOVERY_SESSION"
            # if scn.do_not_ask_again:
            start_lab_session()
        if is_obj[0] == "ERROR":
            gui_status = "ERROR_SESSION"
            gui_err_msg = is_obj[1]
            return


bpy.app.handlers.load_post.append(check_manuelbastionilab_session)


def sync_character_to_props():
    # It's important to avoid problems with Blender undo system
    global mblab_humanoid
    mblab_humanoid.sync_character_data_to_obj_props()
    mblab_humanoid.update_character()


def realtime_update(self, context):
    """
    Update the character while the prop slider moves.
    """
    global mblab_humanoid
    if mblab_humanoid.bodydata_realtime_activated:
        #time1 = time.time()
        scn = bpy.context.scene
        mblab_humanoid.update_character(category_name=scn.morphingCategory, mode="update_realtime")
        mblab_humanoid.sync_gui_according_measures()
        #print("realtime_update: {0}".format(time.time()-time1))


def age_update(self, context):
    global mblab_humanoid
    time1 = time.time()
    if mblab_humanoid.metadata_realtime_activated:
        time1 = time.time()
        mblab_humanoid.calculate_transformation("AGE")


def mass_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.metadata_realtime_activated:
        mblab_humanoid.calculate_transformation("FAT")


def tone_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.metadata_realtime_activated:
        mblab_humanoid.calculate_transformation("MUSCLE")


def modifiers_update(self, context):
    sync_character_to_props()


def set_cycles_render_engine(self, context):
    if context.scene.mblab_use_cycles:
        context.scene.mblab_use_eevee = False


def set_eevee_render_engine(self, context):
    if context.scene.mblab_use_eevee:
        context.scene.mblab_use_cycles = False


def preset_update(self, context):
    """
    Update the character while prop slider moves
    """
    scn = bpy.context.scene
    global mblab_humanoid
    obj = mblab_humanoid.get_object()
    filepath = os.path.join(
        mblab_humanoid.presets_path,
        "".join([obj.preset, ".json"]))
    mblab_humanoid.load_character(filepath, mix=scn.mblab_mix_characters)


def ethnic_update(self, context):
    scn = bpy.context.scene
    global mblab_humanoid
    obj = mblab_humanoid.get_object()
    filepath = os.path.join(
        mblab_humanoid.phenotypes_path,
        "".join([obj.ethnic, ".json"]))
    mblab_humanoid.load_character(filepath, mix=scn.mblab_mix_characters)


def material_update(self, context):
    global mblab_humanoid
    if mblab_humanoid.material_realtime_activated:
        mblab_humanoid.update_materials(update_textures_nodes=False)


def measure_units_update(self, context):
    global mblab_humanoid
    mblab_humanoid.sync_gui_according_measures()


def human_expression_update(self, context):
    global mblab_shapekeys
    scn = bpy.context.scene
    mblab_shapekeys.sync_expression_to_gui()


def restpose_update(self, context):
    global mblab_humanoid
    armature = mblab_humanoid.get_armature()
    filepath = os.path.join(
        mblab_humanoid.restposes_path,
        "".join([armature.rest_pose, ".json"]))
    mblab_retarget.load_pose(filepath, armature)


def malepose_update(self, context):
    global mblab_retarget
    armature = utils.get_active_armature()
    filepath = os.path.join(
        mblab_retarget.maleposes_path,
        "".join([armature.male_pose, ".json"]))
    mblab_retarget.load_pose(filepath, use_retarget=True)


def femalepose_update(self, context):
    global mblab_retarget
    armature = utils.get_active_armature()
    filepath = os.path.join(
        mblab_retarget.femaleposes_path,
        "".join([armature.female_pose, ".json"]))
    mblab_retarget.load_pose(filepath, use_retarget=True)


def init_morphing_props(humanoid_instance):
    for prop in humanoid_instance.character_data:
        setattr(
            bpy.types.Object,
            prop,
            bpy.props.FloatProperty(
                name=prop,
                min=-5.0,
                max=5.0,
                soft_min=0.0,
                soft_max=1.0,
                precision=3,
                default=0.5,
                update=realtime_update))


def init_measures_props(humanoid_instance):
    for measure_name, measure_val in humanoid_instance.morph_engine.measures.items():
        setattr(
            bpy.types.Object,
            measure_name,
            bpy.props.FloatProperty(
                name=measure_name, min=0.0, max=500.0,
                default=measure_val))
    humanoid_instance.sync_gui_according_measures()


def init_categories_props(humanoid_instance):
    categories_enum = []
    for category in mblab_humanoid.get_categories():
        categories_enum.append(
            (category.name, category.name, category.name))

    bpy.types.Scene.morphingCategory = bpy.props.EnumProperty(
        items=categories_enum,
        update = modifiers_update,
        name="变形类别")


def init_restposes_props(humanoid_instance):
    if humanoid_instance.exists_rest_poses_database():
        restpose_items = algorithms.generate_items_list(humanoid_instance.restposes_path)
        bpy.types.Object.rest_pose = bpy.props.EnumProperty(
            items=restpose_items,
            name="静止姿势",
            default=restpose_items[0][0],
            update=restpose_update)


def init_maleposes_props():
    global mblab_retarget
    if mblab_retarget.maleposes_exist:
        if not hasattr(bpy.types.Object, 'male_pose'):
            malepose_items = algorithms.generate_items_list(mblab_retarget.maleposes_path)
            bpy.types.Object.male_pose = bpy.props.EnumProperty(
                items=malepose_items,
                name="男性姿势",
                default=malepose_items[0][0],
                update=malepose_update)


def init_femaleposes_props():
    global mblab_retarget
    if mblab_retarget.femaleposes_exist:
        if not hasattr(bpy.types.Object, 'female_pose'):
            femalepose_items = algorithms.generate_items_list(mblab_retarget.femaleposes_path)
            bpy.types.Object.female_pose = bpy.props.EnumProperty(
                items=femalepose_items,
                name="女性姿势",
                default=femalepose_items[0][0],
                update=femalepose_update)


def init_expression_props():
    for expression_name in mblab_shapekeys.expressions_labels:
        if not hasattr(bpy.types.Object, expression_name):
            setattr(
                bpy.types.Object,
                expression_name,
                bpy.props.FloatProperty(
                    name=expression_name,
                    min=0.0,
                    max=1.0,
                    precision=3,
                    default=0.0,
                    update=human_expression_update))


def init_presets_props(humanoid_instance):
    if humanoid_instance.exists_preset_database():
        preset_items = algorithms.generate_items_list(humanoid_instance.presets_path)
        bpy.types.Object.preset = bpy.props.EnumProperty(
            items=preset_items,
            name="类型",
            update=preset_update)


def init_ethnic_props(humanoid_instance):
    if humanoid_instance.exists_phenotype_database():
        ethnic_items = algorithms.generate_items_list(humanoid_instance.phenotypes_path)
        bpy.types.Object.ethnic = bpy.props.EnumProperty(
            items=ethnic_items,
            name="遗传表型",
            update=ethnic_update)


def init_metaparameters_props(humanoid_instance):
    for meta_data_prop in humanoid_instance.character_metaproperties.keys():
        upd_function = None

        if "age" in meta_data_prop:
            upd_function = age_update
        if "mass" in meta_data_prop:
            upd_function = mass_update
        if "tone" in meta_data_prop:
            upd_function = tone_update
        if "last" in meta_data_prop:
            upd_function = None

        if "last_" not in meta_data_prop:
            setattr(
                bpy.types.Object,
                meta_data_prop,
                bpy.props.FloatProperty(
                    name=meta_data_prop, min=-1.0, max=1.0,
                    precision=3,
                    default=0.0,
                    update=upd_function))


def init_material_parameters_props(humanoid_instance):

    for material_data_prop, value in humanoid_instance.character_material_properties.items():
        setattr(
            bpy.types.Object,
            material_data_prop,
            bpy.props.FloatProperty(
                name=material_data_prop,
                min=0.0,
                max=1.0,
                precision=2,
                update=material_update,
                default=value))


def angle_update_0(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_0
    mblab_retarget.correct_bone_angle(0, value)


def angle_update_1(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_1
    mblab_retarget.correct_bone_angle(1, value)


def angle_update_2(self, context):
    global mblab_retarget
    scn = bpy.context.scene
    value = scn.mblab_rot_offset_2
    mblab_retarget.correct_bone_angle(2, value)


def get_character_items(self, context):
    items = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if algorithms.get_template_model(obj) is not None:
                items.append((obj.name, obj.name, obj.name))
    return items


def get_proxy_items(self, context):
    items = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if algorithms.get_template_model(obj) is None:
                items.append((obj.name, obj.name, obj.name))
    if len(items) == 0:
        items = [("NO_PROXY_FOUND","找不到替代物","找不到替代物")]
    return items


def get_proxy_items_from_library(self, context):
    items = mblab_proxy.assets_models
    return items


def update_proxy_library(self, context):
    mblab_proxy.update_assets_models()


def load_proxy_item(self, context):
    scn = bpy.context.scene
    mblab_proxy.load_asset(scn.mblab_assets_models)


# init_expression_props()

bpy.types.Scene.mblab_proxy_library = bpy.props.StringProperty(
            name="库文件夹",
            description="资源混合文件的文件夹",
            default="",
            maxlen=1024,
            update=update_proxy_library,
            subtype='DIR_PATH')

bpy.types.Scene.mblab_fitref_name = bpy.props.EnumProperty(
        items=get_character_items,
        name="角色")

bpy.types.Scene.mblab_proxy_name = bpy.props.EnumProperty(
        items=get_proxy_items,
        name="替代物")


bpy.types.Scene.mblab_final_prefix = bpy.props.StringProperty(
        name="前缀",
        description="最终模型，骨架和材质的名称前缀。 如果没有，它将自动生成" ,
        default="")

bpy.types.Scene.mblab_rot_offset_0 = bpy.props.FloatProperty(
    name="Tweak rot X",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_0,
    default=0.0)

bpy.types.Scene.mblab_rot_offset_1 = bpy.props.FloatProperty(
    name="Tweak rot Y",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_1,
    default=0.0)

bpy.types.Scene.mblab_rot_offset_2 = bpy.props.FloatProperty(
    name="Tweak rot Z",
    min=-1,
    max=1,
    precision=2,
    update=angle_update_2,
    default=0.0)

bpy.types.Scene.mblab_proxy_offset = bpy.props.FloatProperty(
    name="Offset",
    min=0,
    max=100,
    default=0)

bpy.types.Scene.mblab_proxy_threshold = bpy.props.FloatProperty(
        name="影响",
        min=0,
        max=1000,
        default=20)

bpy.types.Scene.mblab_use_ik = bpy.props.BoolProperty(
    name="使用反向动力学",
    default=False,
    description="使用反向动力学骨架")

bpy.types.Scene.mblab_use_muscle = bpy.props.BoolProperty(
    name="使用基本肌肉",
    default=False,
    description="使用基本肌肉骨架")

bpy.types.Scene.mblab_remove_all_modifiers = bpy.props.BoolProperty(
    name="移除修改器",
    default=False,
    description="如果选中，将删除所有修改器，除了将从最终角色中移除骨架（位移，细分，矫正平滑等）之外）")

bpy.types.Scene.mblab_use_cycles = bpy.props.BoolProperty(
    name="使用 Cycles 材质（皮肤着色器需要）",
    default=True,
    update=set_cycles_render_engine,
    description="为了使用皮肤编辑器和着色器，需要这样做（强烈推荐）")

bpy.types.Scene.mblab_use_eevee = bpy.props.BoolProperty(
    name="使用 EEVEE 材料（Blender 2.8 皮肤着色器需要）",
    default=False,
    update=set_eevee_render_engine,
    description="这是使用皮肤编辑器和着色器所必需的")

bpy.types.Scene.mblab_use_lamps = bpy.props.BoolProperty(
    name="使用肖像工作室光源（推荐）",
    default=True,
    description="添加一组针对肖像优化的光源。 在皮肤设计中有用（推荐）")

bpy.types.Scene.mblab_show_measures = bpy.props.BoolProperty(
    name="身体尺寸",
    description="显示尺寸控件",
    update=modifiers_update)

bpy.types.Scene.mblab_measure_filter = bpy.props.StringProperty(
    name="Filter",
    default="",
    description="Filter the measures to show")

bpy.types.Scene.mblab_expression_filter = bpy.props.StringProperty(
    name="Filter",
    default="",
    description="Filter the expressions to show")

bpy.types.Scene.mblab_mix_characters = bpy.props.BoolProperty(
    name="与当前的混合",
    description="Mix templates")

bpy.types.Scene.mblab_template_name = bpy.props.EnumProperty(
    items=mblab_humanoid.template_types,
    name="Select",
    default="human_female_base")

bpy.types.Scene.mblab_character_name = bpy.props.EnumProperty(
    items=mblab_humanoid.humanoid_types,
    name="Select",
    default="f_ca01")

bpy.types.Scene.mblab_assets_models = bpy.props.EnumProperty(
    items=get_proxy_items_from_library,
    update=load_proxy_item,
    name="资源模型")   


bpy.types.Scene.mblab_transfer_proxy_weights = bpy.props.BoolProperty(
    name="从身体到替代物转移权重（替换现有）",
    description="如果替代物已经装配了权重，它们将被替换为从角色主体投射的权重",
    default=True)

bpy.types.Scene.mblab_save_images_and_backup = bpy.props.BoolProperty(
    name="保存图像并备份角色",
    description="保存皮肤着色器中的所有图像，并以 json 格式备份角色",
    default=True)

bpy.types.Object.mblab_use_inch = bpy.props.BoolProperty(
    name="英寸",
    update=measure_units_update,
    description="使用英寸而不是厘米")

bpy.types.Scene.mblab_export_proportions = bpy.props.BoolProperty(
    name="包含比例",
    description="在导出的角色文件中包含比例")

bpy.types.Scene.mblab_export_materials = bpy.props.BoolProperty(
    name="包含材质",
    default=True,
    description="在导出的角色文件中包含材料")

bpy.types.Scene.mblab_show_texture_load_save = bpy.props.BoolProperty(
    name="导入导出图像",
    description="显示控件以导入和导出纹理图像")

bpy.types.Scene.mblab_add_mask_group = bpy.props.BoolProperty(
    name="添加蒙版顶点组",
    description="创建一个新的顶点组并使用它作为替代物下的身体蒙版。",
    default=False)

bpy.types.Scene.mblab_preserve_mass = bpy.props.BoolProperty(
    name="脂肪",
    description="保持当前的相对脂肪百分比")

bpy.types.Scene.mblab_preserve_height = bpy.props.BoolProperty(
    name="身高",
    description="保持当前角色身高")

bpy.types.Scene.mblab_preserve_tone = bpy.props.BoolProperty(
    name="肌肉",
    description="保留当前的相对肌肉百分比")

bpy.types.Scene.mblab_preserve_fantasy = bpy.props.BoolProperty(
    name="幻想",
    description="保留当前的幻想变形量。 例如，从具有零幻想元素的角色开始，所有生成的角色将具有零幻想元素")

bpy.types.Scene.mblab_preserve_body = bpy.props.BoolProperty(
    name="身体",
    description="保留身体特征")

bpy.types.Scene.mblab_preserve_face = bpy.props.BoolProperty(
    name="脸部",
    description="保留脸部特征，但不保留头部形状")

bpy.types.Scene.mblab_preserve_phenotype = bpy.props.BoolProperty(
    name="遗传表型",
    description="保留性状特征，例如属于同一家庭的人")

bpy.types.Scene.mblab_set_tone_and_mass = bpy.props.BoolProperty(
    name="使用修正过的肌肉和脂肪值",
    description=" 为脂肪和肌肉启用 使用滑动条 UI 修正过 的设置")

bpy.types.Scene.mblab_body_mass = bpy.props.FloatProperty(
    name="身体脂肪",
    min=0.0,
    max=1.0,
    default=0.5,
    description="保留当前的角色体重")

bpy.types.Scene.mblab_body_tone = bpy.props.FloatProperty(
    name="身体肌肉",
    min=0.0,
    max=1.0,
    default=0.5,
    description="保留当前的角色体重")

bpy.types.Scene.mblab_random_engine = bpy.props.EnumProperty(
    items=[("LI", "轻度", "标准差异不大"),
            ("RE", "逼真", "逼真的人物"),
            ("NO", "特征明显", "很有特色的人"),
            ("CA", "讽刺画", "讽刺漫画引擎"),
            ("EX", "极端", "极端的角色")],
    name="引擎",
    default="LI")


class ButtonParametersOff(bpy.types.Operator):

    bl_label = '身体，面部和尺寸参数'
    bl_idname = 'mbast.button_parameters_off'
    bl_description = '关闭细节面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonParametersOn(bpy.types.Operator):
    bl_label = '身体，面部和尺寸参数'
    bl_idname = 'mbast.button_parameters_on'
    bl_description = '打开细节面板（头，鼻子，手，尺寸等......）'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = "parameters"
        sync_character_to_props()
        return {'FINISHED'}


class ButtonUtilitiesOff(bpy.types.Operator):
    bl_label = '辅助工具'
    bl_idname = 'mbast.button_utilities_off'
    bl_description = '关闭辅助工具面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonUtilitiesOn(bpy.types.Operator):
    bl_label = '辅助工具'
    bl_idname = 'mbast.button_utilities_on'
    bl_description = '打开辅助工具面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = "utilities"
        return {'FINISHED'}


class ButtonExpressionsOff(bpy.types.Operator):
    bl_label = '面部表情'
    bl_idname = 'mbast.button_expressions_off'
    bl_description = '关闭表情面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonExpressionOn(bpy.types.Operator):
    bl_label = '面部表情'
    bl_idname = 'mbast.button_expressions_on'
    bl_description = '打开表情面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = "expressions"
        # sync_character_to_props()
        init_expression_props()
        return {'FINISHED'}


class ButtonRandomOff(bpy.types.Operator):
    bl_label = '随机生成器'
    bl_idname = 'mbast.button_random_off'
    bl_description = '关闭随机生成器面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonRandomOn(bpy.types.Operator):
    bl_label = '随机生成器'
    bl_idname = 'mbast.button_random_on'
    bl_description = '打开随机生成器面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'random'
        sync_character_to_props()
        return {'FINISHED'}


class ButtonAutomodellingOff(bpy.types.Operator):

    bl_label = '自动建模工具'
    bl_idname = 'mbast.button_automodelling_off'
    bl_description = '关闭自动建模面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonAutomodellingOn(bpy.types.Operator):
    bl_label = '自动建模工具'
    bl_idname = 'mbast.button_automodelling_on'
    bl_description = '打开自动建模面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'automodelling'
        return {'FINISHED'}


class ButtoRestPoseOff(bpy.types.Operator):
    bl_label = '静止姿势'
    bl_idname = 'mbast.button_rest_pose_off'
    bl_description = '关闭静止姿势面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonRestPoseOn(bpy.types.Operator):
    bl_label = '静止姿势'
    bl_idname = 'mbast.button_rest_pose_on'
    bl_description = '打开静止姿势面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'rest_pose'
        return {'FINISHED'}


class ButtoPoseOff(bpy.types.Operator):
    bl_label = '姿势和动画'
    bl_idname = 'mbast.button_pose_off'
    bl_description = '关闭姿势面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonAssetsOn(bpy.types.Operator):
    bl_label = '资源库'
    bl_idname = 'mbast.button_assets_on'
    bl_description = '打开资源面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = 'assets'
        return {'FINISHED'}


class ButtoAssetsOff(bpy.types.Operator):
    bl_label = '资源库'
    bl_idname = 'mbast.button_assets_off'
    bl_description = '关闭资源面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonPoseOn(bpy.types.Operator):
    bl_label = '姿势和动画'
    bl_idname = 'mbast.button_pose_on'
    bl_description = '打开姿势面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        init_femaleposes_props()
        init_maleposes_props()
        gui_active_panel_fin = 'pose'
        return {'FINISHED'}


class ButtonSkinOff(bpy.types.Operator):
    bl_label = '皮肤编辑器'
    bl_idname = 'mbast.button_skin_off'
    bl_description = '关闭皮肤编辑器面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonSkinOn(bpy.types.Operator):
    bl_label = '皮肤编辑器'
    bl_idname = 'mbast.button_skin_on'
    bl_description = '打开皮肤编辑器面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'skin'
        return {'FINISHED'}


class ButtonViewOptOff(bpy.types.Operator):
    bl_label = '显示选项'
    bl_idname = 'mbast.button_display_off'
    bl_description = '关闭显示选项面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonViewOptOn(bpy.types.Operator):
    bl_label = '显示选项'
    bl_idname = 'mbast.button_display_on'
    bl_description = '打开显示选项面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'display_opt'
        return {'FINISHED'}


class ButtonProxyFitOff(bpy.types.Operator):
    bl_label = '替代物配件'
    bl_idname = 'mbast.button_proxy_fit_off'
    bl_description = '关闭替代物面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = None
        return {'FINISHED'}


class ButtonProxyFitOn(bpy.types.Operator):
    bl_label = '替代物配件'
    bl_idname = 'mbast.button_proxy_fit_on'
    bl_description = '打开替代物面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel_fin
        gui_active_panel_fin = 'proxy_fit'
        return {'FINISHED'}


class ButtonFilesOff(bpy.types.Operator):
    bl_label = '文件工具'
    bl_idname = 'mbast.button_file_off'
    bl_description = '关闭文件面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonFilesOn(bpy.types.Operator):
    bl_label = '文件工具'
    bl_idname = 'mbast.button_file_on'
    bl_description = '打开文件面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'file'
        return {'FINISHED'}


class ButtonFinalizeOff(bpy.types.Operator):
    bl_label = '定型工具'
    bl_idname = 'mbast.button_finalize_off'
    bl_description = '关闭定型面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonFinalizeOn(bpy.types.Operator):
    bl_label = '定型工具'
    bl_idname = 'mbast.button_finalize_on'
    bl_description = '打开定型面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'finalize'
        return {'FINISHED'}


class ButtonLibraryOff(bpy.types.Operator):
    bl_label = '角色库'
    bl_idname = 'mbast.button_library_off'
    bl_description = '关闭角色库面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = None
        return {'FINISHED'}


class ButtonLibraryOn(bpy.types.Operator):
    bl_label = '角色库'
    bl_idname = 'mbast.button_library_on'
    bl_description = '打开角色库面板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global gui_active_panel
        gui_active_panel = 'library'
        return {'FINISHED'}


class ButtonFinalizedCorrectRot(bpy.types.Operator):
    bl_label = '调整选定的骨骼'
    bl_idname = 'mbast.button_adjustrotation'
    bl_description = '使用骨骼角度的偏移来校正动画'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        mblab_retarget.get_bone_rot_type()

        if mblab_retarget.rot_type in ["EULER", "QUATERNION"]:
            offsets = mblab_retarget.get_offset_values()
            scn.mblab_rot_offset_0 = offsets[0]
            scn.mblab_rot_offset_1 = offsets[1]
            scn.mblab_rot_offset_2 = offsets[2]
            mblab_retarget.correction_is_sync = True
        return {'FINISHED'}


class UpdateSkinDisplacement(bpy.types.Operator):
    """
    Calculate and apply the skin displacement
    """
    bl_label = '更新替换'
    bl_idname = 'mbast.skindisplace_calculate'
    bl_description = '使用替换修改器计算并应用皮肤细节'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        """
        Calculate and apply the skin displacement
        """
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()
        return {'FINISHED'}


class DisableSubdivision(bpy.types.Operator):
    """
    Disable subdivision surface
    """
    bl_label = '禁用细分预览'
    bl_idname = 'mbast.subdivision_disable'
    bl_description = '禁用细分修改器'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_subd_visibility() == True:
            mblab_humanoid.set_subd_visibility(False)
        return {'FINISHED'}


class EnableSubdivision(bpy.types.Operator):
    """
    Enable subdivision surface
    """
    bl_label = '启用细分预览'
    bl_idname = 'mbast.subdivision_enable'
    bl_description = '启用细分预览（警告：它会减慢变形速度）'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_subd_visibility() == False:
            mblab_humanoid.set_subd_visibility(True)
        return {'FINISHED'}


class DisableSmooth(bpy.types.Operator):

    bl_label = '禁用矫正平滑'
    bl_idname = 'mbast.corrective_disable'
    bl_description = '在视口中禁用矫正平滑修改器'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_smooth_visibility() == True:
            mblab_humanoid.set_smooth_visibility(False)
        return {'FINISHED'}


class EnableSmooth(bpy.types.Operator):

    bl_label = '启用矫正平滑'
    bl_idname = 'mbast.corrective_enable'
    bl_description = '在视口中启用矫正平滑修改器'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_smooth_visibility() == False:
            mblab_humanoid.set_smooth_visibility(True)
        return {'FINISHED'}


class DisableDisplacement(bpy.types.Operator):
    """
    Disable displacement modifier
    """
    bl_label = '禁用位移预览'
    bl_idname = 'mbast.displacement_disable'
    bl_description = '禁用位移修改器'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_disp_visibility() == True:
            mblab_humanoid.set_disp_visibility(False)
        return {'FINISHED'}


class EnableDisplacement(bpy.types.Operator):
    """
    Enable displacement modifier
    """
    bl_label = '启用位移预览'
    bl_idname = 'mbast.displacement_enable'
    bl_description = '启用位移预览（警告：它会减慢变形速度）'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        scn = bpy.context.scene

        if mblab_humanoid.get_disp_visibility() == False:
            mblab_humanoid.set_disp_visibility(True)
        return {'FINISHED'}


class FinalizeCharacterAndImages(bpy.types.Operator, ExportHelper):
    """
        Convert the character in a standard Blender model
    """
    bl_label = '使用纹理定型并备份'
    bl_idname = 'mbast.finalize_character_and_images'
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
        )
    bl_description = '完成，保存所有纹理并在形态键中转换参数。 警告：转换后，使用 ManuelbastioniLAB 工具不再可以修改角色'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        global gui_status
        # TODO unique function in humanoid class
        scn = bpy.context.scene
        armature = mblab_humanoid.get_armature()

        mblab_humanoid.correct_expressions(correct_all=True)

        if not utils.is_ik_armature(armature):
            mblab_humanoid.set_rest_pose()
        if scn.mblab_remove_all_modifiers:
            mblab_humanoid.remove_modifiers()

        mblab_humanoid.sync_internal_data_with_mesh()
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()
        mblab_humanoid.save_backup_character(self.filepath)
        mblab_humanoid.save_all_textures(self.filepath)

        mblab_humanoid.morph_engine.convert_all_to_blshapekeys()
        mblab_humanoid.delete_all_properties()
        mblab_humanoid.rename_materials(scn.mblab_final_prefix)
        mblab_humanoid.update_bendy_muscles()
        mblab_humanoid.rename_obj(scn.mblab_final_prefix)
        mblab_humanoid.rename_armature(scn.mblab_final_prefix)
        gui_status = "NEW_SESSION"
        return {'FINISHED'}


class FinalizeCharacter(bpy.types.Operator):
    """
    Convert the character in a standard Blender model
    """
    bl_label = '定型'
    bl_idname = 'mbast.finalize_character'
    bl_description = '定型转换形态键中的参数。 警告：转换后，使用 ManuelbastioniLAB 工具不再可以修改角色'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        global mblab_humanoid
        global gui_status
        scn = bpy.context.scene
        armature = mblab_humanoid.get_armature()

        mblab_humanoid.correct_expressions(correct_all=True)

        if not utils.is_ik_armature(armature):
            mblab_humanoid.set_rest_pose()
        if scn.mblab_remove_all_modifiers:
            mblab_humanoid.remove_modifiers()

        mblab_humanoid.sync_internal_data_with_mesh()

        mblab_humanoid.morph_engine.convert_all_to_blshapekeys()
        mblab_humanoid.update_displacement()
        mblab_humanoid.update_materials()

        mblab_humanoid.delete_all_properties()
        mblab_humanoid.rename_materials(scn.mblab_final_prefix)
        mblab_humanoid.update_bendy_muscles()
        mblab_humanoid.rename_obj(scn.mblab_final_prefix)
        mblab_humanoid.rename_armature(scn.mblab_final_prefix)

        gui_status = "NEW_SESSION"
        return {'FINISHED'}


class ResetParameters(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = '重置角色'
    bl_idname = 'mbast.reset_allproperties'
    bl_description = '重置所有角色参数'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.reset_character()
        return {'FINISHED'}


class ResetExpressions(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = '重置表达式'
    bl_idname = 'mbast.reset_expression'
    bl_description = '重置表达式'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_shapekeys
        mblab_shapekeys.reset_expressions_gui()
        return {'FINISHED'}

# class LoadAssets(bpy.types.Operator):
    # """
    # Load assets from library
    # """
    # bl_label = 'Load model from assets library'
    # bl_idname = 'mbast.load_assets_element'
    # bl_description = 'Load the element selected from the assets library'
    # bl_context = 'objectmode'
    # bl_options = {'REGISTER', 'INTERNAL','UNDO'}

    # def execute(self, context):
        # scn = bpy.context.scene
        # mblab_proxy.load_asset(scn.mblab_assets_models)
        # return {'FINISHED'}


class InsertExpressionKeyframe(bpy.types.Operator):
    """Reset all morphings."""
    bl_label = '插入关键帧'
    bl_idname = 'mbast.keyframe_expression'
    bl_description = '在当前时间插入关键帧表达式'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_shapekeys
        mblab_shapekeys.keyframe_expression()
        return {'FINISHED'}


class Reset_category(bpy.types.Operator):
    """Reset the parameters for the currently selected category"""
    bl_label = '重置类别'
    bl_idname = 'mbast.reset_categoryonly'
    bl_description = '重置当前类别的参数'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.reset_category(scn.morphingCategory)
        return {'FINISHED'}


class CharacterGenerator(bpy.types.Operator):
    """Generate a new character using the specified parameters"""
    bl_label = '生成'
    bl_idname = 'mbast.character_generator'
    bl_description = '根据参数生成新角色。'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        rnd_values = {"LI": 0.05, "RE": 0.1, "NO": 0.2, "CA": 0.3, "EX": 0.5}
        rnd_val = rnd_values[scn.mblab_random_engine]
        p_face = scn.mblab_preserve_face
        p_body = scn.mblab_preserve_body
        p_mass = scn.mblab_preserve_mass
        p_tone = scn.mblab_preserve_tone
        p_height = scn.mblab_preserve_height
        p_phenotype = scn.mblab_preserve_phenotype
        set_tone_mass = scn.mblab_set_tone_and_mass
        b_tone = scn.mblab_body_tone
        b_mass = scn.mblab_body_mass
        p_fantasy = scn.mblab_preserve_fantasy

        mblab_humanoid.generate_character(rnd_val, p_face, p_body, p_mass, p_tone,
                                          p_height, p_phenotype, set_tone_mass, b_mass, b_tone, p_fantasy)
        return {'FINISHED'}


class ExpDisplacementImage(bpy.types.Operator, ExportHelper):
    """Export texture maps for the character"""
    bl_idname = "mbast.export_dispimage"
    bl_label = "保存置换贴图"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_body_displacement_texture(self.filepath)
        return {'FINISHED'}


class ExpDermalImage(bpy.types.Operator, ExportHelper):
    """Export texture maps for the character"""
    bl_idname = "mbast.export_dermimage"
    bl_label = "保存真皮贴图"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class ExpAllImages(bpy.types.Operator, ExportHelper):
    """Export all texture maps for the character"""
    bl_idname = "mbast.export_allimages"
    bl_label = "导出所有贴图"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.save_all_textures(self.filepath)
        return {'FINISHED'}


class ExpCharacter(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast.export_character"
    bl_label = "导出角色"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        mblab_humanoid.save_character(self.filepath, scn.mblab_export_proportions, scn.mblab_export_materials)
        return {'FINISHED'}


class ExpMeasures(bpy.types.Operator, ExportHelper):
    """Export parameters for the character"""
    bl_idname = "mbast.export_measures"
    bl_label = "导出尺寸"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.export_measures(self.filepath)
        return {'FINISHED'}


class ImpCharacter(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.import_character"
    bl_label = "导入角色"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid

        char_data = mblab_humanoid.load_character(self.filepath)
        return {'FINISHED'}


class ImpMeasures(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.import_measures"
    bl_label = "导入尺寸"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.import_measures(self.filepath)
        return {'FINISHED'}


class LoadDermImage(bpy.types.Operator, ImportHelper):
    """Import texture maps for the character"""
    bl_idname = "mbast.import_dermal"
    bl_label = "加载真皮图像"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.load_body_dermal_texture(self.filepath)
        return {'FINISHED'}


class LoadDispImage(bpy.types.Operator, ImportHelper):
    """Import texture maps for the character"""
    bl_idname = "mbast.import_displacement"
    bl_label = "加载位移图像"
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(
        default="*.png",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.load_body_displacement_texture(self.filepath)
        return {'FINISHED'}


class FitProxy(bpy.types.Operator):

    bl_label = '适配替代物'
    bl_idname = 'mbast.proxy_fit'
    bl_description = '使所选替代物适合角色'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        offset = scn.mblab_proxy_offset/1000
        threshold = scn.mblab_proxy_threshold/1000
        mblab_proxy.fit_proxy_object(offset, threshold, scn.mblab_add_mask_group, scn.mblab_transfer_proxy_weights)
        return {'FINISHED'}


class RemoveProxy(bpy.types.Operator):

    bl_label = '移除配件'
    bl_idname = 'mbast.proxy_removefit'
    bl_description = '移除配件，以便可以修改替代物，然后重新安装'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scn = bpy.context.scene
        mblab_proxy.remove_fitting()
        return {'FINISHED'}


class ApplyMeasures(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = '更新角色'
    bl_idname = 'mbast.measures_apply'
    bl_description = '使角色适合尺寸'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_GUI=True)
        return {'FINISHED'}


class AutoModelling(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = '自动建模'
    bl_idname = 'mbast.auto_modelling'
    bl_description = '分析网格形式并返回一个类似的人类'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_current_obj=True)
        return {'FINISHED'}


class AutoModellingMix(bpy.types.Operator):
    """Fit the character to the measures"""

    bl_label = '平均化自动建模'
    bl_idname = 'mbast.auto_modelling_mix'
    bl_description = '返回具有多个插值的类似人类，使其最接近平均值'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        mblab_humanoid.automodelling(use_measures_from_current_obj=True, mix=True)
        return {'FINISHED'}


class SaveRestPose(bpy.types.Operator, ExportHelper):
    """Export pose"""
    bl_idname = "mbast.restpose_save"
    bl_label = "保存自定义静止姿势"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        armature = mblab_humanoid.get_armature()
        mblab_retarget.save_pose(armature, self.filepath)
        return {'FINISHED'}


class LoadRestPose(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.restpose_load"
    bl_label = "加载自定义静止姿势"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid, mblab_retarget
        armature = mblab_humanoid.get_armature()
        mblab_retarget.load_pose(self.filepath, armature, use_retarget=False)
        return {'FINISHED'}


class SavePose(bpy.types.Operator, ExportHelper):
    """Export pose"""
    bl_idname = "mbast.pose_save"
    bl_label = "保存姿势"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_humanoid
        armature = utils.get_active_armature()
        mblab_retarget.save_pose(armature, self.filepath)
        return {'FINISHED'}


class LoadPose(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.pose_load"
    bl_label = "加载姿势"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.load_pose(self.filepath, use_retarget=True)
        return {'FINISHED'}


class ResetPose(bpy.types.Operator):
    """Import parameters for the character"""
    bl_idname = "mbast.pose_reset"
    bl_label = "重置姿势"
    bl_context = 'objectmode'
    bl_description = '重置骨架的角度'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.reset_pose()
        return {'FINISHED'}


class LoadBvh(bpy.types.Operator, ImportHelper):
    """Import parameters for the character"""
    bl_idname = "mbast.load_animation"
    bl_label = "加载动画 (bvh)"
    filename_ext = ".bvh"
    bl_description = '从 bvh 动作捕捉文件导入动画'
    filter_glob: bpy.props.StringProperty(
        default="*.bvh",
        options={'HIDDEN'},
    )
    bl_context = 'objectmode'

    def execute(self, context):
        global mblab_retarget
        mblab_retarget.load_animation(self.filepath)
        return {'FINISHED'}


class CreateFaceRig(bpy.types.Operator):
    bl_idname = "mbast.create_face_rig"
    bl_label = "创建面部绑定"
    bl_description = "创建角色的面部绑定"
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        mblab_shapekeys.update_expressions_data()
        if mblab_shapekeys.model_type != "NONE":
            if not facerig.setup_face_rig():
                self.report({'ERROR'},
                            "面部绑定创建过程失败")
        else:
            self.report({'ERROR'},
                        "选择已完成的MB Lab角色以创建面部绑定")
        return {'FINISHED'}


class StartSession(bpy.types.Operator):
    bl_idname = "mbast.init_character"
    bl_label = "初始化角色"
    bl_description = '创建以上选择的角色'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        start_lab_session()
        return {'FINISHED'}


class LoadTemplate(bpy.types.Operator):
    bl_idname = "mbast.load_base_template"
    bl_label = "导入模板"
    bl_description = '导入用于替代物参考的人形模板'
    bl_context = 'objectmode'
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    def execute(self, context):
        global mblab_humanoid
        scn = bpy.context.scene
        lib_filepath = algorithms.get_blendlibrary_path()
        base_model_name = mblab_humanoid.characters_config[scn.mblab_template_name]["template_model"]
        obj = algorithms.import_object_from_lib(lib_filepath, base_model_name, scn.mblab_template_name)
        if obj:
            obj["manuellab_proxy_reference"] = mblab_humanoid.characters_config[scn.mblab_template_name]["template_model"]
        return {'FINISHED'}


class VIEW3D_PT_tools_ManuelbastioniLAB(bpy.types.Panel):

    bl_label = "MB-Lab {0}.{1}.{2}".format(bl_info["version"][0], bl_info["version"][1], bl_info["version"][2])
    bl_idname = "OBJECT_PT_characters01"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = 'objectmode'
    bl_category = "MB-Lab"

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}

    def draw(self, context):

        global mblab_humanoid, gui_status, gui_err_msg, gui_active_panel
        scn = bpy.context.scene
        icon_expand = "DISCLOSURE_TRI_RIGHT"
        icon_collapse = "DISCLOSURE_TRI_DOWN"

        if gui_status == "ERROR_SESSION":
            box = self.layout.box()
            box.label(text=gui_err_msg, icon="INFO")

        if gui_status == "NEW_SESSION":
            #box = self.layout.box()

            self.layout.label(text="https://github.com/animate1978/MB-Lab")
            self.layout.label(text="创作工具")
            self.layout.prop(scn, 'mblab_character_name')

            if mblab_humanoid.is_ik_rig_available(scn.mblab_character_name):
                self.layout.prop(scn, 'mblab_use_ik')
            if mblab_humanoid.is_muscle_rig_available(scn.mblab_character_name):
                self.layout.prop(scn, 'mblab_use_muscle')

            self.layout.prop(scn, 'mblab_use_cycles')
            self.layout.prop(scn, 'mblab_use_eevee')
            if scn.mblab_use_cycles or scn.mblab_use_eevee:
                self.layout.prop(scn, 'mblab_use_lamps')
            self.layout.operator('mbast.init_character')

        if gui_status != "ACTIVE_SESSION":
            self.layout.label(text=" ")
            self.layout.label(text="创作后的工具")

            # face rig button
            self.layout.operator('mbast.create_face_rig')

            if gui_active_panel_fin != "assets":
                self.layout.operator('mbast.button_assets_on', icon=icon_expand)
            else:
                self.layout.operator('mbast.button_assets_off', icon=icon_collapse)
                #assets_status = mblab_proxy.validate_assets_fitting()
                box = self.layout.box()

                box.prop(scn, 'mblab_proxy_library')
                box.prop(scn, 'mblab_assets_models')
                # box.operator('mbast.load_assets_element')
                box.label(text="要调整资源，请使用替代物配件工具", icon='INFO')

            if gui_active_panel_fin != "pose":
                self.layout.operator('mbast.button_pose_on', icon=icon_expand)
            else:
                self.layout.operator('mbast.button_pose_off', icon=icon_collapse)
                box = self.layout.box()

                armature = utils.get_active_armature()
                if armature is not None and not utils.is_ik_armature(armature):
                    box.enabled = True
                    sel_gender = algorithms.get_selected_gender()
                    if sel_gender == "FEMALE":
                        if mblab_retarget.femaleposes_exist:
                            box.prop(armature, "female_pose")
                    if sel_gender == "MALE":
                        if mblab_retarget.maleposes_exist:
                            box.prop(armature, "male_pose")
                    box.operator("mbast.pose_load", icon='IMPORT')
                    box.operator("mbast.pose_save", icon='EXPORT')
                    box.operator("mbast.pose_reset", icon='ARMATURE_DATA')
                    box.operator("mbast.load_animation", icon='IMPORT')
                else:
                    box.enabled = False
                    box.label(text="请选择实验室角色（不支持 IK）", icon='INFO')

            if gui_active_panel_fin != "expressions":
                self.layout.operator('mbast.button_expressions_on', icon=icon_expand)
            else:
                self.layout.operator('mbast.button_expressions_off', icon=icon_collapse)
                box = self.layout.box()
                mblab_shapekeys.update_expressions_data()
                if mblab_shapekeys.model_type != "NONE":
                    box.enabled = True
                    box.prop(scn, 'mblab_expression_filter')
                    box.operator("mbast.keyframe_expression", icon="ACTION")
                    if mblab_shapekeys.expressions_data:
                        obj = algorithms.get_active_body()
                        for expr_name in sorted(mblab_shapekeys.expressions_data.keys()):
                            if hasattr(obj, expr_name):
                                if scn.mblab_expression_filter in expr_name:
                                    box.prop(obj, expr_name)
                    box.operator("mbast.reset_expression", icon="RECOVER_LAST")
                else:
                    box.enabled = False
                    box.label(text="没有表情形态键", icon='INFO')

            if gui_active_panel_fin != "proxy_fit":
                self.layout.operator('mbast.button_proxy_fit_on', icon=icon_expand)
            else:
                self.layout.operator('mbast.button_proxy_fit_off', icon=icon_collapse)
                fitting_status, proxy_obj, reference_obj = mblab_proxy.get_proxy_fitting_ingredients()

                box = self.layout.box()
                box.label(text="替代物配件")
                box.label(text="请选择角色和替代物：")
                box.prop(scn, 'mblab_fitref_name')
                box.prop(scn, 'mblab_proxy_name')                
                if fitting_status == "NO_REFERENCE":
                    #box.enabled = False
                    box.label(text="角色无效", icon="ERROR")
                    box.label(text="可能的原因：")
                    box.label(text="- 角色是用其他版本实验室创建的")
                    box.label(text="- 自定义建模更改了角色拓扑")                    
                    box.label(text="- 角色拓扑被修改器改变了(精简,细分,等等..)")
                if fitting_status == "SAME_OBJECTS":                    
                    box.label(text="替代物和角色不能是同一个对象", icon="ERROR") 
                if fitting_status == "CHARACTER_NOT_FOUND":                   
                    box.label(text="找不到角色", icon="ERROR") 
                if fitting_status == "PROXY_NOT_FOUND":                   
                    box.label(text="找不到替代物", icon="ERROR") 
                if fitting_status == 'OK':                    
                    box.label(text="替代物已准备就绪。", icon="INFO")
                    proxy_compatib = mblab_proxy.validate_assets_compatibility(proxy_obj, reference_obj)                    
                    
                    if proxy_compatib == "WARNING":
                        box.label(text="替代物似乎不是为所选角色设计的。", icon="ERROR")                    
                    
                    box.prop(scn, 'mblab_proxy_offset')
                    box.prop(scn, 'mblab_proxy_threshold')
                    box.prop(scn, 'mblab_add_mask_group')
                    box.prop(scn, 'mblab_transfer_proxy_weights')
                    box.operator("mbast.proxy_fit", icon="MOD_CLOTH")
                    box.operator("mbast.proxy_removefit", icon="MOD_CLOTH")
                if fitting_status == 'WRONG_SELECTION':
                    box.enabled = False
                    box.label(text="请只选择两个对象：人形和替代物", icon="INFO")
                if fitting_status == 'NO_REFERENCE_SELECTED':
                    box.enabled = False
                    box.label(text="未选择有效的人形模板", icon="INFO")
                if fitting_status == 'NO_MESH_SELECTED':
                    box.enabled = False
                    box.label(text="选定的替代物不是网格", icon="INFO")

            if gui_active_panel_fin != "utilities":
                self.layout.operator('mbast.button_utilities_on', icon=icon_expand)
            else:
                self.layout.operator('mbast.button_utilities_off', icon=icon_collapse)

                box = self.layout.box()
                box.label(text="选择替代物参考")
                box.prop(scn, 'mblab_template_name')
                box.operator('mbast.load_base_template')

                box = self.layout.box()
                box.label(text="骨骼旋转偏移")
                box.operator('mbast.button_adjustrotation', icon='BONE_DATA')
                mblab_retarget.check_correction_sync()
                if mblab_retarget.is_animated_bone == "VALID_BONE":
                    if mblab_retarget.correction_is_sync:
                        box.prop(scn, 'mblab_rot_offset_0')
                        box.prop(scn, 'mblab_rot_offset_1')
                        box.prop(scn, 'mblab_rot_offset_2')
                else:
                    box.label(text=mblab_retarget.is_animated_bone)

        if gui_status == "ACTIVE_SESSION":
            obj = mblab_humanoid.get_object()
            armature = mblab_humanoid.get_armature()
            if obj and armature:
                #box = self.layout.box()

                if mblab_humanoid.exists_transform_database():
                    self.layout.label(text="创作工具")
                    x_age = getattr(obj, 'character_age', 0)
                    x_mass = getattr(obj, 'character_mass', 0)
                    x_tone = getattr(obj, 'character_tone', 0)
                    age_lbl = round((15.5*x_age**2)+31*x_age+33)
                    mass_lbl = round(50*(x_mass+1))
                    tone_lbl = round(50*(x_tone+1))
                    lbl_text = "年龄：{0}岁  脂肪（质量）：{1}%  肌肉：{2}% ".format(age_lbl,mass_lbl,tone_lbl)
                    self.layout.label(text=lbl_text, icon="RNA")
                    for meta_data_prop in sorted(mblab_humanoid.character_metaproperties.keys()):
                        if "last" not in meta_data_prop:
                            self.layout.prop(obj, meta_data_prop)
                    self.layout.operator("mbast.reset_allproperties", icon="RECOVER_LAST")
                    if mblab_humanoid.get_subd_visibility() == True:
                        self.layout.label(
                            text="提示：性能不足的设备，请在下面的“显示选项”中禁用细分", icon='INFO')

                if gui_active_panel != "library":
                    self.layout.operator('mbast.button_library_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_library_off', icon=icon_collapse)
                    box = self.layout.box()

                    box.label(text="角色库")
                    if mblab_humanoid.exists_preset_database():
                        box.prop(obj, "preset")
                    if mblab_humanoid.exists_phenotype_database():
                        box.prop(obj, "ethnic")
                    box.prop(scn, 'mblab_mix_characters')

                if gui_active_panel != "random":
                    self.layout.operator('mbast.button_random_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_random_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.prop(scn, "mblab_random_engine")
                    box.prop(scn, "mblab_set_tone_and_mass")
                    if scn.mblab_set_tone_and_mass:
                        box.prop(scn, "mblab_body_mass")
                        box.prop(scn, "mblab_body_tone")

                    box.label(text="保留：")
                    box.prop(scn, "mblab_preserve_mass")
                    box.prop(scn, "mblab_preserve_height")
                    box.prop(scn, "mblab_preserve_tone")
                    box.prop(scn, "mblab_preserve_body")
                    box.prop(scn, "mblab_preserve_face")
                    box.prop(scn, "mblab_preserve_phenotype")
                    box.prop(scn, "mblab_preserve_fantasy")

                    box.operator('mbast.character_generator', icon="FILE_REFRESH")

                if gui_active_panel != "parameters":
                    self.layout.operator('mbast.button_parameters_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_parameters_off', icon=icon_collapse)

                    box = self.layout.box()
                    mblab_humanoid.bodydata_realtime_activated = True
                    if mblab_humanoid.exists_measure_database():
                        box.prop(scn, 'mblab_show_measures')
                    split = box.split()

                    col = split.column()
                    col.label(text="参数")
                    col.prop(scn, "morphingCategory")

                    for prop in mblab_humanoid.get_properties_in_category(scn.morphingCategory):
                        if hasattr(obj, prop):
                            col.prop(obj, prop)

                    if mblab_humanoid.exists_measure_database() and scn.mblab_show_measures:
                        col = split.column()
                        col.label(text="尺寸")
                        col.label(text="实验功能", icon='ERROR')
                        col.prop(obj, 'mblab_use_inch')
                        col.prop(scn, 'mblab_measure_filter')
                        col.operator("mbast.measures_apply")

                        m_unit = "cm"
                        if obj.mblab_use_inch:
                            m_unit = "Inches"
                        col.label(text="高度：{0} {1}".format(round(getattr(obj, "body_height_Z", 0), 3), m_unit))
                        for measure in sorted(mblab_humanoid.measures.keys()):
                            if measure != "body_height_Z":
                                if hasattr(obj, measure):
                                    if scn.mblab_measure_filter in measure:
                                        col.prop(obj, measure)

                        col.operator("mbast.export_measures", icon='EXPORT')
                        col.operator("mbast.import_measures", icon='IMPORT')

                    sub = box.box()
                    sub.label(text="重置")
                    sub.operator("mbast.reset_categoryonly")

                if mblab_humanoid.exists_measure_database():
                    if gui_active_panel != "automodelling":
                        self.layout.operator('mbast.button_automodelling_on', icon=icon_expand)
                    else:
                        self.layout.operator('mbast.button_automodelling_off', icon=icon_collapse)
                        box = self.layout.box()
                        box.operator("mbast.auto_modelling")
                        box.operator("mbast.auto_modelling_mix")
                else:
                    box = self.layout.box()
                    box.enabled = False
                    box.label(text="自动建模不适用于此角色", icon='INFO')

                if mblab_humanoid.exists_rest_poses_database():
                    if gui_active_panel != "rest_pose":
                        self.layout.operator('mbast.button_rest_pose_on', icon=icon_expand)
                    else:
                        self.layout.operator('mbast.button_rest_pose_off', icon=icon_collapse)
                        box = self.layout.box()

                        if utils.is_ik_armature(armature):
                            box.enabled = False
                            box.label(text="静止姿势不适用于 反向动力学（IK）骨架", icon='INFO')
                        else:
                            box.enabled = True
                            box.prop(armature, "rest_pose")

                            box.operator("mbast.restpose_load")
                            box.operator("mbast.restpose_save")

                if gui_active_panel != "skin":
                    self.layout.operator('mbast.button_skin_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_skin_off', icon=icon_collapse)

                    box = self.layout.box()
                    box.enabled = True
                    if scn.render.engine != 'CYCLES' and scn.render.engine != 'BLENDER_EEVEE':
                        box.enabled = False
                        box.label(text="皮肤编辑器需要 Cycles 或 EEVEE", icon='INFO')

                    if mblab_humanoid.exists_displace_texture():
                        box.operator("mbast.skindisplace_calculate")
                        box.label(text="您需要启用 细分预览 和 替换 才能在视口中查看显示", icon='INFO')

                    for material_data_prop in sorted(mblab_humanoid.character_material_properties.keys()):
                        box.prop(obj, material_data_prop)

                if gui_active_panel != "file":
                    self.layout.operator('mbast.button_file_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_file_off', icon=icon_collapse)
                    box = self.layout.box()
                    box.prop(scn, 'mblab_show_texture_load_save')
                    if scn.mblab_show_texture_load_save:

                        if mblab_humanoid.exists_dermal_texture():
                            sub = box.box()
                            sub.label(text="皮肤纹理")
                            sub.operator("mbast.export_dermimage", icon='EXPORT')
                            sub.operator("mbast.import_dermal", icon='IMPORT')

                        if mblab_humanoid.exists_displace_texture():
                            sub = box.box()
                            sub.label(text="替换纹理")
                            sub.operator("mbast.export_dispimage", icon='EXPORT')
                            sub.operator("mbast.import_displacement", icon='IMPORT')

                        sub = box.box()
                        sub.label(text="导出皮肤着色器中使用的所有图像")
                        sub.operator("mbast.export_allimages", icon='EXPORT')
                    box.prop(scn, 'mblab_export_proportions')
                    box.prop(scn, 'mblab_export_materials')
                    box.operator("mbast.export_character", icon='EXPORT')
                    box.operator("mbast.import_character", icon='IMPORT')

                if gui_active_panel != "finalize":
                    self.layout.operator('mbast.button_finalize_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_finalize_off', icon=icon_collapse)
                    box = self.layout.box()
                    box.prop(scn, 'mblab_save_images_and_backup')
                    box.prop(scn, 'mblab_remove_all_modifiers')
                    box.prop(scn, 'mblab_final_prefix')
                    if scn.mblab_save_images_and_backup:
                        box.operator("mbast.finalize_character_and_images", icon='FREEZE')
                    else:
                        box.operator("mbast.finalize_character", icon='FREEZE')

                if gui_active_panel != "display_opt":
                    self.layout.operator('mbast.button_display_on', icon=icon_expand)
                else:
                    self.layout.operator('mbast.button_display_off', icon=icon_collapse)
                    box = self.layout.box()

                    if mblab_humanoid.exists_displace_texture():
                        if mblab_humanoid.get_disp_visibility() == False:
                            box.operator("mbast.displacement_enable", icon='MOD_DISPLACE')
                        else:
                            box.operator("mbast.displacement_disable", icon='X')
                    if mblab_humanoid.get_subd_visibility() == False:
                        box.operator("mbast.subdivision_enable", icon='MOD_SUBSURF')
                        box.label(text="细分预览非常占用 CPU", icon='INFO')
                    else:
                        box.operator("mbast.subdivision_disable", icon='X')
                        box.label(text="禁用细分以提高性能", icon='ERROR')
                    if mblab_humanoid.get_smooth_visibility() == False:
                        box.operator("mbast.corrective_enable", icon='MOD_SMOOTH')
                    else:
                        box.operator("mbast.corrective_disable", icon='X')

                self.layout.label(text=" ")
                self.layout.label(text="创作后的工具")
                self.layout.label(
                    text="后期创作工具（表情，姿势，之类 ..）不适用于未完成的角色", icon="INFO")

            else:
                gui_status = "NEW_SESSION"


classes = (
    ButtonParametersOff,
    ButtonParametersOn,
    ButtonUtilitiesOff,
    ButtonUtilitiesOn,
    ButtonExpressionsOff,
    ButtonExpressionOn,
    ButtonRandomOff,
    ButtonRandomOn,
    ButtonAutomodellingOff,
    ButtonAutomodellingOn,
    ButtoRestPoseOff,
    ButtonRestPoseOn,
    ButtoPoseOff,
    ButtonAssetsOn,
    ButtoAssetsOff,
    ButtonPoseOn,
    ButtonSkinOff,
    ButtonSkinOn,
    ButtonViewOptOff,
    ButtonViewOptOn,
    ButtonProxyFitOff,
    ButtonProxyFitOn,
    ButtonFilesOff,
    ButtonFilesOn,
    ButtonFinalizeOff,
    ButtonFinalizeOn,
    ButtonLibraryOff,
    ButtonLibraryOn,
    ButtonFinalizedCorrectRot,
    UpdateSkinDisplacement,
    DisableSubdivision,
    EnableSubdivision,
    DisableSmooth,
    EnableSmooth,
    DisableDisplacement,
    EnableDisplacement,
    FinalizeCharacterAndImages,
    FinalizeCharacter,
    ResetParameters,
    ResetExpressions,
    InsertExpressionKeyframe,
    Reset_category,
    CharacterGenerator,
    ExpDisplacementImage,
    ExpDermalImage,
    ExpAllImages,
    ExpCharacter,
    ExpMeasures,
    ImpCharacter,
    ImpMeasures,
    LoadDermImage,
    LoadDispImage,
    FitProxy,
    RemoveProxy,
    ApplyMeasures,
    AutoModelling,
    AutoModellingMix,
    SaveRestPose,
    LoadRestPose,
    SavePose,
    LoadPose,
    ResetPose,
    LoadBvh,
    StartSession,
    CreateFaceRig,
    LoadTemplate,
    VIEW3D_PT_tools_ManuelbastioniLAB,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
