import json
# coreografia de TL_P3re_PC063_00 (escena del muelle P3R): 2 actores, 5.58s
scene = {
 "duration": 5.58,
 "fps": 30,
 "actors": [
  {"name": "aegis", "actorPrefab": "PC063_02",
   "rigs": ["PC063_02_body_wholeexport_rig"],
   "clip": "PC063_thief@stand_story",
   "pos": [0.55, 0, 0], "rotY": -75},
  {"name": "wonder", "actorPrefab": "wonder_uniform",
   "rigs": ["wonder_yingyuan_head_wholeexport_rig",
            "wonder_uniform_hair_wholeexport_rig",
            "wonder_uniform_shoes_wholeexport_rig",
            "wonder_uniform_bottom_wholeexport_rig",
            "wonder_uniform_face_wholeexport_rig_bs",
            "wonder_unifom_lod_body_wholeexport_rig"],
   "clip": "wonder_uniform@stand_01",
   "pos": [-0.55, 0, 0.15], "rotY": 75}
 ]}
json.dump(scene, open("unity_projects/scene_full/ExportedProject/Assets/Resources/scene_def.json","w", encoding="utf-8"), indent=1)
print("scene_def.json escrito")
