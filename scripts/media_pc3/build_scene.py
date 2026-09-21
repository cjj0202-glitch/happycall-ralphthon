"""Build the independent N03-M2 Blender scene; never reads company drawings.

Blender 4.5 LTS: blender --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py --
  --layout planning/media/scene-layout-v1.json --output .local/pc3-blender/render
  --mode representatives

The default renders only three review frames. Animation needs a separate explicit mode
after pc1's visual review. Blender execution is required; normal Python is compile-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_contract import SCENE_SEED, FRAME_COUNT, evaluate_motion, load_layout
from look_presets import settings_for
from environment_detail import environment_specs
from shadow_settings import configure_shadow_rays


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, default=Path('data/fixtures/cases.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepare', 'representatives', 'short', 'animation'], default='representatives')
    parser.add_argument('--engine', choices=['eevee', 'cycles'], default='eevee')
    parser.add_argument('--camera', choices=['cctv', 'overview'], default='cctv')
    parser.add_argument('--resolution', nargs=2, type=int, default=[1280, 720])
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--shadow-rays', type=int, choices=range(1, 5), default=1)
    parser.add_argument('--look', choices=['baseline', 'contrast_material_v1'], default='baseline')
    parser.add_argument('--environment-detail', choices=['none', 'staging_v1'], default='none')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = parser.parse_args(argv)
    if min(args.resolution) < 64 or max(args.resolution) > 3840 or not 1 <= args.samples <= 256:
        parser.error('Resolution must be 64..3840 and samples 1..256.')
    if args.engine == 'cycles' and args.shadow_rays != 1:
        parser.error('--shadow-rays is EEVEE-only; Cycles allows only the unapplied default 1.')
    if args.mode == 'animation' and args.camera != 'cctv':
        parser.error('Final event candidate must use the fixed registered CCTV camera.')
    if args.mode == 'animation' and (args.look != 'baseline' or args.environment_detail != 'none'):
        parser.error('Look/environment candidates allow prepare, representatives and short only; full animation awaits review.')
    return args


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'name': Path(path).name, 'bytes': Path(path).stat().st_size, 'sha256': h.hexdigest()}


def material(name, color, metallic=0.0, roughness=0.5, noise=False, bump_strength=0.16, bump_distance=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if noise:
        tex = tree.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 4.0 if name == 'Concrete' else 45.0
        tex.inputs['Detail'].default_value = 3.0
        ramp = tree.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (*[v * 0.76 for v in color], 1)
        ramp.color_ramp.elements[1].color = (*[min(1, v * 1.12) for v in color], 1)
        tree.links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
        tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        bump = tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = bump_strength
        bump.inputs['Distance'].default_value = bump_distance if bump_distance is not None else (0.008 if name == 'Concrete' else 0.001)
        tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def cube(name, location, dimensions, mat, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Manufactured edge radius', 'BEVEL')
        mod.width, mod.segments = bevel, 3
    if parent:
        obj.parent = parent
    return obj


def cylinder(name, location, radius, depth, mat, axis='Z'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    if axis == 'Y':
        obj.rotation_euler.x = math.pi / 2
    elif axis == 'X':
        obj.rotation_euler.y = math.pi / 2
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    bevel = obj.modifiers.new('Rolled edge', 'BEVEL')
    bevel.width, bevel.segments = 0.004, 2
    return obj


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def camera(name, position, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens, data.sensor_width = lens, 36
    data.sensor_fit = 'HORIZONTAL'
    data.clip_start, data.clip_end = 0.1, 120
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)
    return obj


def area(name, position, target, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size, data.color = energy, 'DISK', size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)


def build(layout, args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    random.seed(SCENE_SEED)
    look = settings_for(args.look)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if args.engine == 'eevee' else 'CYCLES'
    if args.engine == 'cycles':
        scene.cycles.device, scene.cycles.samples = 'CPU', args.samples
        scene.cycles.use_denoising = True
    elif hasattr(scene, 'eevee'):
        if hasattr(scene.eevee, 'taa_render_samples'):
            scene.eevee.taa_render_samples = args.samples
        if hasattr(scene.eevee, 'use_gtao'):
            scene.eevee.use_gtao = True
    scene.render.resolution_x, scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    if hasattr(scene.render, 'use_motion_blur'):
        scene.render.use_motion_blur = False
    scene.render.fps, scene.frame_start, scene.frame_end = 24, 1, FRAME_COUNT
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    scene.world = bpy.data.worlds.new('Independent synthetic warehouse environment')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.58, 0.67, 0.8, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = look['worldStrength']

    mats = {
        'floor': material('Concrete', look['concrete']['color'], roughness=look['concrete']['roughness'], noise=True,
                          bump_strength=look['concrete']['bumpStrength'], bump_distance=look['concrete']['bumpDistance']),
        'steel': material('Brushed galvanized steel', look['steel']['color'], metallic=look['steel']['metallic'], roughness=look['steel']['roughness']),
        'frame': material('Powder coated graphite', (0.085, 0.105, 0.12), metallic=0.45, roughness=0.4),
        'belt': material('Black rubber belt', (0.022, 0.028, 0.035), roughness=0.82, noise=True),
        'yellow': material('Safety yellow', (0.95, 0.61, 0.035), metallic=0.1, roughness=0.37),
        'blue': material('Blue injection plastic', (0.018, 0.08, 0.31), roughness=0.34),
        'card': material('Corrugated cardboard', (0.48, 0.31, 0.16), roughness=0.9, noise=True),
        'tape': material('Packing tape', (0.59, 0.43, 0.23), roughness=0.24),
        'white': material('Paper and wall', (0.73, 0.75, 0.73), roughness=0.72),
        'orange': material('Rack beam orange', (0.70, 0.19, 0.035), metallic=0.15, roughness=0.42),
        'dark': material('Expansion joint', (0.055, 0.065, 0.068), roughness=0.9),
    }
    width, depth = layout['floor']['width'], layout['floor']['depth']
    cube('Independent 30 by 18 floor', (width / 2, depth / 2, -0.12), (width, depth, 0.24), mats['floor'])
    for x in range(5, int(width), 5):
        cube('Floor expansion seam X', (x, depth / 2, 0.001), (0.009, depth, 0.002), mats['dark'])
    for y in range(3, int(depth), 3):
        cube('Floor expansion seam Y', (width / 2, y, 0.001), (width, 0.009, 0.002), mats['dark'])
    cube('Rear warehouse wall', (15, 18.08, 3), (30, 0.16, 6), mats['white'])
    for x in range(1, 30, 3):
        cube('Wall vertical rib', (x, 17.96, 3), (0.065, 0.065, 6), mats['steel'])
    for x, y in [(3, 11), (10, 13), (22, 13), (28, 13)]:
        cube('Structural column', (x, y, 3), (0.32, 0.32, 6), mats['steel'], 0.02)
        cube('Column protective base', (x, y, 0.50), (0.38, 0.38, 1), mats['yellow'], 0.01)

    # Sparse context keeps the selected sorter readable, with open working aisles.
    for bay in range(3):
        x, y = 2.4 + bay * 2.1, 13.8
        for dx in [-0.9, 0.9]:
            for dy in [-0.65, 0.65]:
                cube('Rack upright', (x + dx, y + dy, 1.9), (0.08, 0.08, 3.8), mats['blue'], 0.008)
        for z in [0.18, 1.45, 2.72]:
            cube('Rack shelf', (x, y, z), (1.95, 1.38, 0.10), mats['frame'], 0.008)
            for dy in [-0.70, 0.70]:
                cube('Rack beam', (x, y + dy, z), (2.0, 0.08, 0.14), mats['orange'], 0.01)
            for dx in [-0.48, 0.18]:
                h = random.uniform(0.48, 0.64)
                cube('Background corrugated carton', (x + dx, y, z + 0.05 + h / 2), (0.57, 0.86, h), mats['card'], 0.015)

    path = layout['visualPath']['points']
    x0, x_end, y_main, surface = path[0][0] - 0.75, 23.0, path[0][1], path[0][2]
    branch_x, branch_end = path[-1][0], path[-1][1] - 0.65
    # Roller tops and transfer belt share the same actual contact plane.
    cube('Main lower belt support', ((x0 + x_end) / 2, y_main, surface - 0.09), (x_end - x0, 1.25, 0.06), mats['belt'], 0.01)
    for side in [-1, 1]:
        cube('Main conveyor side channel', ((x0 + x_end) / 2, y_main + side * 0.70, surface - 0.12), (x_end - x0, 0.09, 0.22), mats['steel'], 0.009)
    x = x0 + 0.1
    while x < x_end:
        if not branch_x - 2.0 <= x <= branch_x + 0.7:
            cylinder('Contact roller', (x, y_main, surface - 0.05), 0.05, 1.28, mats['steel'], 'Y')
        x += 0.20
    cube('Branch transfer black belt', (branch_x - 0.65, y_main, surface - 0.035), (2.7, 1.30, 0.07), mats['belt'], 0.008)
    cube('CH02 outfeed belt', (branch_x, (branch_end + y_main - 0.65) / 2, surface - 0.035), (1.40, y_main - 0.65 - branch_end, 0.07), mats['belt'], 0.008)
    for side in [-1, 1]:
        cube('CH02 side frame', (branch_x + side * 0.76, (branch_end + y_main - 0.65) / 2, surface - 0.13), (0.09, y_main - 0.65 - branch_end, 0.24), mats['steel'], 0.008)

    def leg(x, y):
        cube('Conveyor steel leg', (x, y, 0.34), (0.09, 0.09, 0.68), mats['frame'], 0.006)
        cube('Bolted foot on floor', (x, y, 0.015), (0.23, 0.20, 0.03), mats['steel'], 0.005)
        for dx in [-0.075, 0.075]:
            cylinder('Foot anchor bolt', (x + dx, y, 0.035), 0.013, 0.014, mats['frame'])
    for x in [x0 + 0.3, 11.5, 14, 16.2, 19.8, 22.7]:
        for y in [y_main - 0.63, y_main + 0.63]:
            leg(x, y)
        cube('Conveyor lower cross brace', (x, y_main, 0.24), (0.055, 1.30, 0.065), mats['frame'], 0.005)
    for y in [4.1, 5.5, 6.4]:
        for x in [branch_x - 0.68, branch_x + 0.68]:
            leg(x, y)

    cube('North yellow safety rail', ((x0 + x_end) / 2, y_main + 0.78, 1.06), (x_end - x0, 0.065, 0.10), mats['yellow'], 0.018)
    for left, right in [(x0, branch_x - 0.90), (branch_x + 0.90, x_end)]:
        cube('South interrupted safety rail', ((left + right) / 2, y_main - 0.79, 1.06), (right - left, 0.065, 0.10), mats['yellow'], 0.018)
    for side in [-1, 1]:
        cube('Outfeed side guard', (branch_x + side * 0.79, (branch_end + 6.5) / 2, 1.02), (0.06, 6.5 - branch_end, 0.14), mats['yellow'], 0.015)
    for x in [10, 12.5, 15, 17, 20, 22.5]:
        # Span both rail and side channel in Y, with 30 mm vertical overlap
        # into the channel. The old north-only post missed its channel by 10 mm.
        cube('North guard support', (x, y_main + 0.74, 0.935), (0.06, 0.16, 0.25), mats['frame'], 0.005)
        # These X positions stay outside the interrupted branch opening.
        cube('South guard support', (x, y_main - 0.745, 0.935), (0.06, 0.16, 0.25), mats['frame'], 0.005)
    for y in [4.1, 5.5, 6.25]:
        for side in [-1, 1]:
            cube('Outfeed guard support', (branch_x + side * 0.775, y, 0.915), (0.10, 0.06, 0.21), mats['frame'], 0.005)

    cube('Electrical cabinet', (21.2, 8.7, 0.49), (0.65, 0.36, 0.98), mats['steel'], 0.035)
    cube('Cabinet door inset', (21.2, 8.505, 0.51), (0.57, 0.025, 0.86), mats['frame'], 0.012)
    cube('Cabinet handle', (21.42, 8.475, 0.55), (0.025, 0.04, 0.17), mats['steel'], 0.009)
    # Empty stationary plastic tote is background equipment, never tote A or B.
    tote_x, tote_y = 12.3, 2.0
    cube('Empty background plastic tote bottom', (tote_x, tote_y, 0.07), (0.75, 0.50, 0.14), mats['blue'], 0.025)
    for side in [-1, 1]:
        cube('Plastic tote long wall', (tote_x, tote_y + side * 0.235, 0.22), (0.75, 0.035, 0.30), mats['blue'], 0.012)
        cube('Plastic tote end wall', (tote_x + side * 0.355, tote_y, 0.22), (0.035, 0.44, 0.30), mats['blue'], 0.012)
    # Floor marks remain spatial cues, not evidence of a real warehouse plan.
    for y in [0.55, 2.50]:
        cube('Dispatch staging line', (17.4, y, 0.006), (12.5, 0.07, 0.012), mats['yellow'])
    for x in [11.2, 14.3, 17.4, 20.5, 23.6]:
        cube('Dispatch lane division', (x, 1.53, 0.006), (0.065, 2.0, 0.012), mats['yellow'])

    anchor = layout['eventAnchor']
    root = bpy.data.objects.new(anchor['visualObjectId'], None)
    bpy.context.collection.objects.link(root)
    root['visualObjectId'] = anchor['visualObjectId']
    root['businessToteId'] = 'null (unknown)'
    root['trackSource'] = 'synthetic-scene-ground-truth'
    # Origin is on the contact plane; all local mesh points have z >= 0.
    body = cube('Selected synthetic parcel carton', (0, 0, 0.175), (0.62, 0.42, 0.35), mats['card'], 0.012, root)
    tape = cube('Parcel taped lid', (0, 0, 0.352), (0.075, 0.418, 0.004), mats['tape'], 0.001, root)
    paper = cube('Blank synthetic parcel label', (0.15, -0.04, 0.352), (0.16, 0.13, 0.004), mats['white'], 0.002, root)
    tracked = [body, tape, paper]
    for frame in range(1, FRAME_COUNT + 1):
        motion = evaluate_motion((frame - 1) / 24, layout)
        root.location = motion['position']
        root.rotation_euler.z = motion['yaw_radians']
        root.keyframe_insert(data_path='location', frame=frame)
        root.keyframe_insert(data_path='rotation_euler', frame=frame)

    spec = layout['camera']
    cctv = camera(spec['id'], spec['position'], spec['lookAt'], spec['lensMm'])
    overview = camera('SYN-OVERVIEW-NOT-CCTV', (32, -9, 24), (15, 9, 0), 36)
    scene.camera = cctv if args.camera == 'cctv' else overview
    area('Large soft loading-side light', (15, 0, 10), (16, 7, 0), look['lightEnergies']['Large soft loading-side light'], 8, (0.88, 0.94, 1.0))
    area('Ceiling key', (15, 10, 9), (17, 7, 0), look['lightEnergies']['Ceiling key'], 6, (1.0, 0.94, 0.84))
    area('Warehouse fill', (5, 10, 7), (14, 8, 0), look['lightEnergies']['Warehouse fill'], 5, (0.87, 0.93, 1.0))
    area('Chute rim', (25, 7, 7), (18, 6, 0), look['lightEnergies']['Chute rim'], 4, (1.0, 0.93, 0.80))
    # This watermark survives a raw PNG/full-screen playback; detailed Korean UI is separate.
    scene.render.use_stamp = True
    scene.render.use_stamp_note = True
    scene.render.stamp_note_text = 'SYNTHETIC SCENE / NOT CCTV | W-W3 | business tote UNKNOWN | illustrative elapsed frames'
    for flag in ['date', 'time', 'render_time', 'frame', 'camera', 'lens', 'scene', 'marker', 'filename', 'sequencer_strip']:
        name = 'use_stamp_' + flag
        if hasattr(scene.render, name):
            setattr(scene.render, name, False)
    scene.render.stamp_font_size = 18
    scene.render.stamp_foreground = (1, 1, 1, 1)
    scene.render.stamp_background = (0.012, 0.02, 0.03, 0.86)
    # Appended after all original scene construction. No random draws or edits
    # to existing objects/materials/camera/lights/animation/tracked are made.
    for prop in environment_specs(args.environment_detail)['objects']:
        if prop['primitive'] == 'cube':
            obj = cube(prop['name'], prop['location'], prop['dimensions'], mats[prop['material']], prop['bevel'])
        else:
            obj = cylinder(prop['name'], prop['location'], prop['radius'], prop['depth'], mats[prop['material']], prop['axis'])
        obj['role'] = prop['role']
        obj['synthetic'] = True
        obj['tracked'] = False
        obj['motion'] = 'static'
        # Blender custom properties cannot store JSON null; the authoritative
        # report below preserves businessToteId as null, never a business ID.
        obj['businessToteId'] = 'null (unassigned environment prop)'
    return scene, root, tracked


def tracks(scene, layout, tracked):
    output, clipped = [], []
    for frame in range(1, FRAME_COUNT + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        points = [obj.matrix_world @ Vector(corner) for obj in tracked for corner in obj.bound_box]
        projected = [world_to_camera_view(scene, scene.camera, point) for point in points]
        x0, x1 = min(p.x for p in projected), max(p.x for p in projected)
        y0, y1 = 1 - max(p.y for p in projected), 1 - min(p.y for p in projected)
        fully_visible = min(p.z for p in projected) > 0 and x0 >= 0 and y0 >= 0 and x1 <= 1 and y1 <= 1
        if not fully_visible:
            clipped.append(frame)
        motion = evaluate_motion((frame - 1) / 24, layout)
        contact_gap = min(p.z for p in points) - motion['position'][2]
        if abs(contact_gap) > 1e-5:
            raise RuntimeError(f'Parcel contact plane mismatch frame={frame}: {contact_gap}')
        output.append({'frame': frame, 'elapsedSeconds': (frame - 1) / 24,
                       'visualObjectId': layout['eventAnchor']['visualObjectId'], 'businessToteId': None,
                       'worldPosition': motion['position'], 'yawRadians': motion['yaw_radians'],
                       'phase': motion['phase'], 'bboxNormalizedXYXY': [x0, y0, x1, y1],
                       'fullyInFrame': fully_visible, 'contactPlaneGapMeters': contact_gap})
    return {'source': 'synthetic-scene-ground-truth', 'synthetic': True, 'eventAnchor': layout['eventAnchor'],
            'coordinateSpace': 'normalized-image-top-left', 'fps': 24, 'frameCount': FRAME_COUNT,
            'resolution': [scene.render.resolution_x, scene.render.resolution_y],
            'clockMode': layout['animation']['clockMode'],
            'cameraId': scene.camera.name, 'cameraPosition': list(scene.camera.location),
            'cameraLensMm': scene.camera.data.lens, 'sensorWidthMm': scene.camera.data.sensor_width,
            'occlusionTested': False,
            'notice': 'Projected 3D bounds, not AI detections or business tote tracking. Visibility does not test occlusion.',
            'frames': output, 'clippedFrames': clipped}


def main():
    args = arguments()
    layout = load_layout(args.layout, fixture_path=args.fixture)
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise RuntimeError('Output directory is not empty; choose a new run directory. No overwrite.')
    started = time.time()
    scene, parcel, tracked = build(layout, args)
    shadow_rays = configure_shadow_rays(scene, args.engine, args.shadow_rays)
    tracking = tracks(scene, layout, tracked)
    (args.output / 'tracks.json').write_text(json.dumps(tracking, ensure_ascii=False, indent=2), encoding='utf-8')
    scene.frame_set(1)
    blend_path = args.output / 'case-0002-ww3.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path.resolve()))
    selected_frames = []
    if args.mode == 'representatives':
        selected_frames = [1, 133, FRAME_COUNT]
    elif args.mode == 'short':
        selected_frames = list(range(73, 145))
    elif args.mode == 'animation':
        selected_frames = list(range(1, FRAME_COUNT + 1))
    rendered = []
    for frame in selected_frames:
        scene.frame_set(frame)
        path = args.output / f'frame-{frame:04d}.png'
        scene.render.filepath = str(path.resolve())
        began = time.time()
        bpy.ops.render.render(write_still=True)
        rendered.append({**digest(path), 'frame': frame, 'elapsedSeconds': (frame - 1) / 24, 'renderSeconds': time.time() - began})
    report = {'schemaVersion': 'pc3-blender-candidate-v1', 'synthetic': True,
              'status': 'unreviewed-render-candidate' if rendered else 'scene-prepared-not-rendered',
              'visualGateAccepted': False, 'mainRegistration': False, 'seed': SCENE_SEED,
              'blenderVersion': bpy.app.version_string, 'engine': scene.render.engine,
              'engineDevice': 'CPU' if args.engine == 'cycles' else 'Blender EEVEE runtime device; inspect actual log',
              'requestedSamples': args.samples, 'resolution': args.resolution, 'fps': 24,
              'shadowRays': shadow_rays,
              'runtimeSamples': {'property': 'scene.cycles.samples' if args.engine == 'cycles' else 'scene.eevee.taa_render_samples',
                                 'value': scene.cycles.samples if args.engine == 'cycles' else getattr(getattr(scene, 'eevee', None), 'taa_render_samples', None),
                                 'note': 'Runtime property readback; null means unverified, not the requested count.'},
              'look': {'name': args.look, 'settings': settings_for(args.look)},
              'environmentDetail': environment_specs(args.environment_detail),
              'colorManagement': {'viewTransform': scene.view_settings.view_transform,
                                  'exposure': scene.view_settings.exposure, 'gamma': scene.view_settings.gamma},
              'candidateDurationSeconds': 12, 'candidateFrameCount': FRAME_COUNT,
              'renderedFrameCount': len(rendered), 'wallSeconds': time.time() - started,
              'layout': digest(args.layout), 'generator': digest(__file__), 'eventAnchor': layout['eventAnchor'],
              'sourceDependencies': [digest(Path(__file__).with_name('scene_contract.py')), digest(Path(__file__).with_name('look_presets.py')),
                                     digest(Path(__file__).with_name('shadow_settings.py'))],
              'cameraId': scene.camera.name, 'clockMode': layout['animation']['clockMode'],
              'representativeFrames': [1, 133, FRAME_COUNT], 'rendered': rendered,
              'blend': digest(blend_path), 'tracks': digest(args.output / 'tracks.json'),
              'clippedFrames': tracking['clippedFrames'], 'occlusionAndVisualContactReviewed': False,
              'videoEncoded': False, 'note': 'Visual review and motion/occlusion inspection remain required. No actual incident reconstruction.'}
    if args.environment_detail != 'none':
        report['sourceDependencies'].append(digest(Path(__file__).with_name('environment_detail.py')))
    (args.output / 'render-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), 'rendered': len(rendered), 'clippedFrames': tracking['clippedFrames'], 'seconds': report['wallSeconds']}))


if __name__ == '__main__':
    main()
