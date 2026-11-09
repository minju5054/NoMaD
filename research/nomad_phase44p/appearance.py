"""Deterministic textures and material-only USD edits, no added geometry."""
import colorsys,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

HERE=Path(__file__).parent;ASSETS=HERE/'textures'
PANELS=tuple(f'Panel{i}_{side}' for i in range(7) for side in ('L','R'))
WALLS=('LeftWall','RightWall','EndWall','StartWall','EndDoor')
# OpenUSD GeomUtilCuboidMeshGenerator topology, used only to author UV primvars.
# https://github.com/PixarAnimationStudios/OpenUSD/blob/release/pxr/imaging/geomUtil/cuboidMeshGenerator.cpp
VERTICES=np.array([[1,1,1],[-1,1,1],[-1,-1,1],[1,-1,1],[-1,-1,-1],[-1,1,-1],[1,1,-1],[1,-1,-1]],float)/2
FACES=((0,1,2,3),(4,5,6,7),(0,6,5,1),(4,7,3,2),(0,3,7,6),(4,2,1,5))


def color(index):
    # Non-magenta hues preserve the frozen DynamicObstacle magenta detector.
    return np.asarray(colorsys.hsv_to_rgb((index*.38196601125)%(2/3),.58,.72))


def pattern(index,size=256):
    yy,xx=np.mgrid[:size,:size];base=color(index)
    stripe=((xx+(index%4)*yy)//(13+index%7))%2
    value=np.where(stripe[...,None],base*.58,base)
    # A unique fixed bit pattern remains recognizable if hue is ambiguous.
    for bit in range(5):
        if (index+1)&(1<<bit):
            lo=12+bit*44;value[18:54,lo:lo+25]=.9
    value[-10:]=.12;value[:8]=.12
    return np.uint8(np.clip(value*255,0,255))


def floor_texture():
    a=np.empty((256,1024,3),np.uint8)
    for i in range(20):
        # Distinct maximum8-bit intensity prevents quantization from merging
        # two distant floor sections that happen to have similar hues.
        tint=.27+.004*i+.16*color(40+i)
        a[:,i*1024//20:(i+1)*1024//20]=np.uint8(tint*255)
    return a


def build_assets():
    ASSETS.mkdir(exist_ok=True)
    for i,name in enumerate((*PANELS,*WALLS)):
        Image.fromarray(pattern(i)).save(ASSETS/(name+'.png'))
    Image.fromarray(floor_texture()).save(ASSETS/'Floor.png')
    return {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(ASSETS.glob('*.png'))}


def cube_uvs():
    uv=[]
    for face in FACES:
        q=VERTICES[list(face)];constant=int(np.argmin(np.ptp(q,axis=0)))
        axes=(0,1) if constant==2 else (0,2) if constant==1 else (1,2)
        uv.extend((q[:,axes]+.5).tolist())
    return uv


def geometry_signature(stage,base):
    result={}
    names={'size','extent','radius','height','axis','points','faceVertexCounts','faceVertexIndices','subdivisionScheme',
           'orientation','visibility','purpose','focalLength','horizontalAperture','verticalAperture','clippingRange','inputs:intensity'}
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith('/World/Materials'):continue
        attrs={}
        for attr in prim.GetAttributes():
            name=attr.GetName()
            if name in names or name.startswith('xformOp:') or name=='xformOpOrder':
                attrs[name]=dict(default=str(attr.Get()),samples=[(float(t),str(attr.Get(t))) for t in attr.GetTimeSamples()])
        result[str(prim.GetPath())]=dict(type=str(prim.GetTypeName()),attributes=attrs)
    return result


def apply(stage,config,base):
    before=geometry_signature(stage,base);bindings=[]
    static={b['id'] for b in config.get('obstacles',[])}
    for prim in list(stage.Traverse()):
        name=prim.GetName()
        if not prim.IsA(base.UsdGeom.Cube) or name not in (*PANELS,*WALLS,'Floor',*static):continue
        material=base.UsdShade.Material.Define(stage,'/World/Materials/Appearance44_'+name)
        shader=base.UsdShade.Shader.Define(stage,material.GetPath().AppendChild('Surface'))
        shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('roughness',base.Sdf.ValueTypeNames.Float).Set(.85)
        shader.CreateInput('opacity',base.Sdf.ValueTypeNames.Float).Set(1.)
        texture=ASSETS/(name+'.png')
        if texture.exists():
            reader=base.UsdShade.Shader.Define(stage,material.GetPath().AppendChild('UV'))
            reader.CreateIdAttr('UsdPrimvarReader_float2');reader.CreateInput('varname',base.Sdf.ValueTypeNames.Token).Set('st')
            reader.CreateOutput('result',base.Sdf.ValueTypeNames.Float2)
            tex=base.UsdShade.Shader.Define(stage,material.GetPath().AppendChild('Texture'))
            tex.CreateIdAttr('UsdUVTexture');tex.CreateInput('file',base.Sdf.ValueTypeNames.Asset).Set(base.Sdf.AssetPath(str(texture)))
            tex.CreateInput('sourceColorSpace',base.Sdf.ValueTypeNames.Token).Set('sRGB')
            tex.CreateInput('st',base.Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),'result')
            tex.CreateOutput('rgb',base.Sdf.ValueTypeNames.Float3)
            shader.CreateInput('diffuseColor',base.Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(),'rgb')
            base.UsdGeom.PrimvarsAPI(prim).CreatePrimvar('st',base.Sdf.ValueTypeNames.TexCoord2fArray,
                base.UsdGeom.Tokens.faceVarying).Set([base.Gf.Vec2f(*q) for q in cube_uvs()])
        else:
            # L2/H2 have no static boxes. Keep generic distinct colors without
            # creating any obstacle if one is absent from the frozen geometry.
            value=color(100+sorted(static).index(name))
            shader.CreateInput('diffuseColor',base.Sdf.ValueTypeNames.Color3f).Set(base.Gf.Vec3f(*value))
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
        base.UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
        bindings.append(dict(prim=str(prim.GetPath()),material=str(material.GetPath()),texture=str(texture) if texture.exists() else None))
    after=geometry_signature(stage,base);assert before==after,'Appearance edit changed geometry/camera/light'
    assert set(PANELS).issubset({Path(r['prim']).name for r in bindings})
    return dict(geometry_identical=True,geometry_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
                bindings=bindings,static_box_count=len(static),dynamic_color='Frozen magenta; distinct from all static palette entries')
