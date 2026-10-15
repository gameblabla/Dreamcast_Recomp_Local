#include ""
#ifndef _NJDEF_H_
#define _NJDEF_H_
#if 0
#define USE_CAST_OBJTYPE
#if 1
#define USE_CHUNK_MODEL
#endif
#endif
#if 0
#define USE_OLD_ANGLE
#endif
#if defined(_M_SH) || defined(_M_IX86)
#define USE_UNSIGNED_TYPE
#endif
#if defined(USE_CAST_OBJTYPE) && defined(_cplusplus)
#ifdef USE_CHUNK_MODEL
#define _OBJPOINTERTYPE (NJS_CNK_OBJECT *)
#else
#define _OBJPOINTERTYPE (NJS_OBJECT *)
#endif
#else
#define _OBJPOINTERTYPE
#endif
#ifndef NULL
#ifdef _cplusplus
#define NULL                (0)
#else
#define NULL                ((void*) 0)
#endif
#endif
#define START          ={
#define END            };
#define UV( _u, _v) (((((long)(_v))<<16)&0xffff0000)|((long)(_u))& 0x0000ffff)
#define Uvn( _u, _v)       (_u), (_v)
#define Uvh( _u, _v)       (_u), (_v)
#define _NJAVAL             (65536.0F/360.0000F)
#define _NJANG1(_a) (long)(_NJAVAL*(_a))
#define _NJANG( _x, _y, _z)                               \
    {(long)(_NJAVAL*(_x)), (long)(_NJAVAL*(_y)), (long)(_NJAVAL*(_z))}
#define _ARGB( _a, _r, _g, _b)                                           \
                ( (unsigned long)((_a)<<24)|(unsigned long)((_r)<<16)    \
                 |(unsigned long)((_g)<<8)|(_b) )
#define ARGB( _a, _r, _g, _b) _ARGB( _a, _r, _g, _b)
#define _NJARGB( _a, _r, _g, _b) _ARGB( _a, _r, _g, _b)
#define TEXN(_texname)     {(_texname), 0x0, 0}
#define TEXN3(_texname, _attr, _texaddr) {(_texname), _attr, _texaddr}
#define TEXTURE_START
#define TEXTURENAME         NJS_TEXNAME
#define TEXTURELIST         NJS_TEXLIST
#define NO_TEXTURE          0
#define TEXTURE_END
#define TextureList
#define TextureNum
#define _SET_CNT(_f) (_f ? NJD_TEXATTR_TEXCONTINUE : 0)
#define _SET_BNK(_b) (((_b) << NJD_TEXBANK_SHIFT) & NJD_TEXBANK_MASK)
#define _SET_BNK2(_b, _g) (_SET_BNK(_b)|((_g) & ~NJD_TEXBANK_MASK))
#define PTEXN(_tname, _cnt, _bnk) {(_tname), _SET_CNT(_cnt), _SET_BNK(_bnk)}
#define PTEXN5(_tname, _attr, _texaddr, _cnt, _bnk)                     \
    {(_tname), _SET_CNT(_cnt)|(_attr), _SET_BNK2(_bnk, _texaddr)}
#define INSTANCE_PROTOTYPE_START
#define INSTANCE_PROTOTYPE_END
#define MATERIAL            NJS_MATERIAL
#define MATSTART           {
#define Diffuse( _a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define Specular( _a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define Exponent( _exp)           (_exp)
#define AttrTexId( _attr, _tid)   ((_attr)|(_tid))
#define AttrFlags( _atf)          ((_atf))
#define MATEND             },
#define MDiff( _a, _r, _g, _b) ((_g) << 8)|(_b), ((_a) << 8)|(_r)
#define MSpec( _a, _r, _g, _b) ((_g) << 8)|(_b), ((_a) << 8)|(_r)
#define MAmbi( _a, _r, _g, _b) ((_g) << 8)|(_b), ((_a) << 8)|(_r)
#define AttrF( _f ) ((_f) & 0xffff), (((_f) >> 16) & 0xffff)
#define VERT( _x, _y, _z)   (_x), (_y), (_z)
#define NORM( _x, _y, _z)   (_x), (_y), (_z)
#define POINT		    NJS_POINT3
#define NORMAL		    NJS_VECTOR
#define VERT_SH( _x, _y, _z)    (_x), (_y), (_z), 0x3f800000
#define NORM_SH( _x, _y, _z)    (_x), (_y), (_z), 0x0
#define NORM32( _x, _y, _z)     ((_x)<<20|(_y)<<10|(_z))
#define D8888( _a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define UFlags( _f)             (_f)
#define NFlags( _f)             (_f)
#define _WPCa( _p)              ((unsigned long)(((_p)*255.0F)/100.0F+0.5F))
#define NFlagsW( _idx, _wp)     (((_WPCa(_wp) & 0xffff)<<16)|((_idx) & 0xffff))
#define _RGB565( _r, _g, _b)                                           \
 ( (((_r) & 0x1f)<<11)|(((_g) & 0x3f)<<5)|((_b) & 0x1f) )
#define _ARGB4444( _a, _r, _g, _b)                                     \
 ( (((_a) & 0xf)<<12)|(((_r) & 0xf)<<8)|(((_g) & 0xf)<<4)|((_b) & 0xf) )
#define D565S565( _r, _g, _b, _sr, _sg, _sb)                           \
 (_RGB565(_r, _g, _b) << 16)|_RGB565(_sr, _sg, _sb)
#define D4444S565( _a, _r, _g, _b, _sr, _sg, _sb)                      \
 (_ARGB4444(_a, _r, _g, _b) << 16)|_RGB565(_sr, _sg, _sb)
#define D16S16(_d, _s)       (((_d)<<16)|(_s))
#define POLYGON              Sint16
#define Strip( _flag, _len) ((_flag)|(_len))
#define StripL( _len)       (_len)
#define StripR( _len)       (_len) * -1
#define POLYNORMAL          NJS_VECTOR
#define STRIPNORMAL         NJS_VECTOR
#define PNORM( _x, _y, _z)  (_x), (_y), (_z)
#define VERTCOLOR           NJS_COLOR
#define _PVN_MAX 32767.0F
#define FtoU(_a_)        ((long)((_a_) * _PVN_MAX) & 0xffffU)
#ifdef USE_UNSIGNED_TYPE
#define Pvn( _x, _y, _z) FtoU(_x), FtoU(_y), FtoU(_z)
#else
#define Pvn( _x, _y, _z) (_x)*_PVN_MAX, (_y)*_PVN_MAX, (_z)*_PVN_MAX
#endif
#define _BuDir(_dx, _dy, _dz) Pvn(_dx, _dy, _dz)
#define _BuUp(_dx, _dy, _dz) Pvn(_dx, _dy, _dz)
#define VERTUV              NJS_COLOR
#define MESHSET             NJS_MESHSET
#define MESHSTART           {
#define MESHEND             },
#define TypeMatId(_type, _mid) ((_type)|(_mid))
#define MeshNum
#define Meshes
#define PolyAttrs
#define PolyNormal
#define VertColor
#define VertUV
#define Center
#define Radius
#define MODEL                NJS_MODEL
#define Model
#define Points
#define Normal
#define Meshset
#define PointNum
#define MeshsetNum
#define Materials
#define MatNum
#define CNKMODEL             NJS_CNK_MODEL
#define CNKModel
#define VList
#define PList
#ifdef USE_UNSIGNED_TYPE
#define VLIST                Uint32
#define PLIST                Uint16
#else
#define VLIST                Sint32
#define PLIST                Sint16
#endif
#define OBJECT               NJS_OBJECT
#define OBJECT_START
#define OBJECT_END
#define EvalFlags( _ef)        (_ef)
#ifdef USE_OLD_ANGLE
#define Position( _x, _y, _z)  (_x), (_y), (_z)
#define Angle( _x, _y, _z)     _NJANG(_x, _y, _z)
#define Scale( _x,  _y,  _z)   (_x), (_y), (_z)
#endif
#define Child               _OBJPOINTERTYPE
#define Sibling             _OBJPOINTERTYPE
#define OPosition(_x, _y, _z)  (_x), (_y), (_z)
#define OAngle(_x, _y, _z)     _NJANG(_x, _y, _z)
#define OScale(_x, _y, _z)     (_x), (_y), (_z)
#define CNKOBJECT            NJS_CNK_OBJECT
#define CNKOBJECT_START
#define CNKOBJECT_END
#define _KEYVAL                (65535.0f/360.0000F)
#define MKEYF( _k, _x, _y, _z)                                      \
    {((Uint32)(_k)), ((float)(_x)), ((float)(_y)), ((float)(_z))}
#define MKEYF1( _k, _a)                                             \
    {((Uint32)(_k)), ((float)(_a))}
#define MKEYF2( _k, _n, _f)                                         \
    {((Uint32)(_k)), ((float)(_n)), ((float)(_f))}
#define MKEYA( _k, _x, _y, _z)                                      \
    {((Uint32)(_k)), ((long)(_KEYVAL*(_x))),                        \
     ((long)(_KEYVAL*(_y))),((long)(_KEYVAL*(_z)))}
#define MKEYA1(_k, _v)        {((Uint32)(_k)),((long)(_KEYVAL*(_v)))}
#define MKEYAX( _k, _a, _x, _y, _z)                                 \
    {((Uint32)(_k)), ((float)((_a))),                               \
     ((float)(_x)), ((float)(_y)), ((float)(_z))}
#define MKEYQ( _k, _a, _x, _y, _z)                                  \
    {((Uint32)(_k)), ((float)((_a))),                               \
     ((float)(_x)), ((float)(_y)), ((float)(_z))}
#define MKEYP(k,x)            {((Uint32)(k)),((void *)(x))}
#define MKEYUI32(_k, _v)      {((Uint32)(_k)),((unsigned long)(_v))}
#define MKEYSI32(_k, _v)      {((Uint32)(_k)),((long)(_v))}
#define MKEYSPOT(_k, _n, _f, _ia, _oa)                              \
    {((Uint32)(_k)), ((float)(_n)),                                 \
    ((float)(_f)), ((long)(_KEYVAL*(_ia))), ((long)(_KEYVAL*(_oa)))}
#define MOTION_START
#define SHAPE_MOTION_START
#define POSITION	NJS_MKEY_F
#define XROTATION	NJS_MKEY_AX
#define QROTATION       NJS_MKEY_QUAT
#define ROTATION	NJS_MKEY_A
#define SCALE		NJS_MKEY_F
#define SCALE2D		NJS_MKEY_F2
#define AXEVECT		NJS_MKEY_AX
#define POINTER		NJS_MKEY_P
#define MDATA1		NJS_MDATA1
#define MDATA2		NJS_MDATA2
#define MDATA3		NJS_MDATA3
#define MDATA4		NJS_MDATA4
#define MDATA5		NJS_MDATA5
#define MOTION		NJS_MOTION
#define ACTION		NJS_ACTION
#define MOTION_END
#define SHAPE_MOTION_END
#define MdataArray
#define MFrameNum
#define MotionBit
#define InterpolFct
#define ObjectHead     _OBJPOINTERTYPE
#define Motion
#define DEFAULT_START
#define DEFAULT_END
#define FBS_ZER   NJD_FBS_ZER
#define FBS_ONE   NJD_FBS_ONE
#define FBS_OC    NJD_FBS_OC
#define FBS_IOC   NJD_FBS_IOC
#define FBS_SA    NJD_FBS_SA
#define FBS_ISA   NJD_FBS_ISA
#define FBS_DA    NJD_FBS_DA
#define FBS_IDA   NJD_FBS_IDA
#define FBD_ZER   NJD_FBD_ZER
#define FBD_ONE   NJD_FBD_ONE
#define FBD_OC    NJD_FBD_OC
#define FBD_IOC   NJD_FBD_IOC
#define FBD_SA    NJD_FBD_SA
#define FBD_ISA   NJD_FBD_ISA
#define FBD_DA    NJD_FBD_DA
#define FBD_IDA   NJD_FBD_IDA
#define FDA_025   NJD_FDA_025
#define FDA_050   NJD_FDA_050
#define FDA_075   NJD_FDA_075
#define FDA_100   NJD_FDA_100
#define FDA_125   NJD_FDA_125
#define FDA_150   NJD_FDA_150
#define FDA_175   NJD_FDA_175
#define FDA_200   NJD_FDA_200
#define FDA_225   NJD_FDA_225
#define FDA_250   NJD_FDA_250
#define FDA_275   NJD_FDA_275
#define FDA_300   NJD_FDA_300
#define FDA_325   NJD_FDA_325
#define FDA_350   NJD_FDA_350
#define FDA_375   NJD_FDA_375
#define FEXP_00   NJD_FEXP_00
#define FEXP_01   NJD_FEXP_01
#define FEXP_02   NJD_FEXP_02
#define FEXP_03   NJD_FEXP_03
#define FEXP_04   NJD_FEXP_04
#define FEXP_05   NJD_FEXP_05
#define FEXP_06   NJD_FEXP_06
#define FEXP_07   NJD_FEXP_07
#define FEXP_08   NJD_FEXP_08
#define FEXP_09   NJD_FEXP_09
#define FEXP_10   NJD_FEXP_10
#define FEXP_11   NJD_FEXP_11
#define FEXP_12   NJD_FEXP_12
#define FEXP_13   NJD_FEXP_13
#define FEXP_14   NJD_FEXP_14
#define FEXP_15   NJD_FEXP_15
#define FEXP_16   NJD_FEXP_16
#define FFL_U    NJD_FFL_U
#define FFL_V    NJD_FFL_V
#define FCL_U    NJD_FCL_U
#define FCL_V    NJD_FCL_V
#define FFM_PS   NJD_FFM_PS
#define FFM_BF   NJD_FFM_BF
#define FFM_TF   NJD_FFM_TF
#define FSS      NJD_FSS
#define FW_START  NJD_FW_START
#define FW_MIDDLE NJD_FW_MIDDLE
#define FW_END    NJD_FW_END
#define FV_CONT    NJD_FV_CONT
#define FST_IL   NJD_FST_IL
#define FST_IS   NJD_FST_IS
#define FST_IA   NJD_FST_IA
#define FST_UA   NJD_FST_UA
#define FST_DB   NJD_FST_DB
#define FST_FL   NJD_FST_FL
#define FST_ENV  NJD_FST_ENV
#define UFO_0    NJD_UFO_0
#define UFO_1    NJD_UFO_1
#define UFO_2    NJD_UFO_2
#define UFO_3    NJD_UFO_3
#define _NB(_ufo, _ns)             (_ufo)|(_ns)
#define Uf1( _ufo1 )               (_ufo1)
#define Uf2( _ufo1, _ufo2 )        (_ufo1), (_ufo2)
#define Uf3( _ufo1, _ufo2, _ufo3 ) (_ufo1), (_ufo2), (_ufo3)
#define CnkEnd()         (NJD_CE)
#define CnkNull()        (NJD_CN)
#define CnkB_BA( _bits)   (_bits)|NJD_CB_BA
#define CnkB_DA( _bits)   (_bits)|NJD_CB_DA
#define CnkB_CP( _bits)   ((_bits)<<8)|NJD_CB_CP
#define CnkB_DP( _bits)   ((_bits)<<8)|NJD_CB_DP
#define CnkT_TID( _bits)  (_bits)|NJD_CT_TID
#define _TID( _bits,_tid) (_bits)|(_tid)
#define CnkT_TID2( _bits) (_bits)|NJD_CT_TID2
#define CnkM_D( _bits)    (_bits)|NJD_CM_D
#define CnkM_S( _bits)    (_bits)|NJD_CM_S
#define CnkM_DS( _bits)   (_bits)|NJD_CM_DS
#define CnkM_A( _bits)    (_bits)|NJD_CM_A
#define CnkM_DA( _bits)   (_bits)|NJD_CM_DA
#define CnkM_AS( _bits)   (_bits)|NJD_CM_AS
#define CnkM_DAS( _bits)  (_bits)|NJD_CM_DAS
#define CnkM_D2( _bits)   (_bits)|NJD_CM_D2
#define CnkM_S2( _bits)   (_bits)|NJD_CM_S2
#define CnkM_DS2( _bits)  (_bits)|NJD_CM_DS2
#define CnkM_A2( _bits)   (_bits)|NJD_CM_A2
#define CnkM_DA2( _bits)  (_bits)|NJD_CM_DA2
#define CnkM_AS2( _bits)  (_bits)|NJD_CM_AS2
#define CnkM_DAS2( _bits) (_bits)|NJD_CM_DAS2
#define CnkM_BU(_bits)    NJD_CM_BU
#define _CkV(_f,_s)       (((_s)<<16)|(_f))
#define CnkV_SH(_f,_s)    (_CkV(_f,_s)|NJD_CV_SH)
#define CnkV_VN_SH(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_SH)
#define CnkV(_f,_s)       (_CkV(_f,_s)|NJD_CV)
#define CnkV_D8(_f,_s)    (_CkV(_f,_s)|NJD_CV_D8)
#define CnkV_UF(_f,_s)    (_CkV(_f,_s)|NJD_CV_UF)
#define CnkV_NF(_f,_s)    (_CkV(_f,_s)|NJD_CV_NF)
#define CnkV_S5(_f,_s)    (_CkV(_f,_s)|NJD_CV_S5)
#define CnkV_S4(_f,_s)    (_CkV(_f,_s)|NJD_CV_S4)
#define CnkV_IN(_f,_s)    (_CkV(_f,_s)|NJD_CV_IN)
#define CnkV_VN(_f, _s)   (_CkV(_f,_s)|NJD_CV_VN)
#define CnkV_VN_D8(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_D8)
#define CnkV_VN_UF(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_UF)
#define CnkV_VN_NF(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_NF)
#define CnkV_VN_S5(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_S5)
#define CnkV_VN_S4(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_S4)
#define CnkV_VN_IN(_f,_s) (_CkV(_f,_s)|NJD_CV_VN_IN)
#define CnkV_VNX(_f,_s)    (_CkV(_f,_s)|NJD_CV_VNX)
#define CnkV_VNX_D8(_f,_s) (_CkV(_f,_s)|NJD_CV_VNX_D8)
#define CnkV_VNX_UF(_f,_s) (_CkV(_f,_s)|NJD_CV_VNX_UF)
#define OffnbIdx( _off, _nb) ((_nb)<<16)|(_off)
#define CnkO_P3(_bits)     NJD_CO_P3
#define CnkO_P4(_bits)     NJD_CO_P4
#define CnkO_ST(_bits)     NJD_CO_ST
#define CnkS(_bits)        (_bits)|NJD_CS
#define CnkS_UVN(_bits)    (_bits)|NJD_CS_UVN
#define CnkS_UVH(_bits)    (_bits)|NJD_CS_UVH
#define CnkS_VN(_bits)     (_bits)|NJD_CS_VN
#define CnkS_UVN_VN(_bits) (_bits)|NJD_CS_UVN_VN
#define CnkS_UVH_VN(_bits) (_bits)|NJD_CS_UVH_VN
#define CnkS_D8(_bits)     (_bits)|NJD_CS_D8
#define CnkS_UVN_D8(_bits) (_bits)|NJD_CS_UVN_D8
#define CnkS_UVH_D8(_bits) (_bits)|NJD_CS_UVH_D8
#define CnkS_2(_bits)      (_bits)|NJD_CS_2
#define CnkS_UVN2(_bits)   (_bits)|NJD_CS_UVN2
#define CnkS_UVH2(_bits)   (_bits)|NJD_CS_UVH2
#define CAMERA                 NJS_CAMERA
#define CAMERA_START           ={
#define CAMERA_END             0.f, 0.f, 0.f, 0.f, 0.f, 0.f};
#define CPosition( _x, _y, _z) (_x), (_y), (_z)
#define CInterest( _x, _y, _z) (_x), (_y), (_z)
#define CRoll( _ang)           (_KEYVAL*(_ang))
#define CAngle( _ang)          (_KEYVAL*(_ang))
#define CNearClip( _n)         (_n)
#define CFarClip( _f)          (_f)
#define CAMERA_ACTION          NJS_CACTION
#define CameraObj
#define CPOSITION	       NJS_MKEY_F
#define CTARGET                NJS_MKEY_F
#define CVECTOR                NJS_MKEY_F
#define CROLL                  NJS_MKEY_A1
#define CANGLE                 NJS_MKEY_A1
#define LIGHT NJS_LIGHT
#define LIGHT_START             = { 0.f, 0.f, 0.f, 0.f,\
                                    0.f, 0.f, 0.f, 0.f,\
                                    0.f, 0.f, 0.f, 0.f,\
                                    0.f, 0.f, 0.f, 0.f,
#define LIGHT_END               };
#define LATTR_START             1, 0,\
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, 0, 0,\
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f, 0.f, 0.f, 0.f, \
                                0.f, 0.f,
#define LATTR_END
#define LStatus( _st)           (_st)
#define LPosition( _x, _y, _z)  (_x), (_y), (_z)
#define LVector( _x, _y, _z)    (_x), (_y), (_z)
#define LType( _t)              (_t)
#define LIntensity( _i)         (_i), (_i), 0.3f
#define LNRange( _n)            (_n)
#define LFRange( _f)            (_f), NULL
#define LIAngle( _i)            (_KEYVAL*(_i))
#define LOAngle( _o)            (_KEYVAL*(_o))
#define LColor( _a, _r, _g, _b) (_a/255.0F), (_r/255.0F), (_g/255.0F), (_b/255.0F)
#define LIGHT_ACTION            NJS_LACTION
#define LightObj
#define LPOSITION               NJS_MKEY_F
#define LVECTOR                 NJS_MKEY_F
#define LTARGET                 NJS_MKEY_F
#define LCOLOR                  NJS_MKEY_UI32
#define LINTENSITY              NJS_MKEY_F1
#define LSPOT_FACTORS           NJS_MKEY_SPOT
#define LPOINT_FACTORS          NJS_MKEY_F2
#define FCS_ZER                 NJD_FCS_ZER
#define FCS_ONE                 NJD_FCS_ONE
#define FCS_OC                  NJD_FCS_OC
#define FCS_IOC                 NJD_FCS_IOC
#define FCS_SA                  NJD_FCS_SA
#define FCS_ISA                 NJD_FCS_ISA
#define FCS_DA                  NJD_FCS_DA
#define FCS_IDA                 NJD_FCS_IDA
#define FCD_ZER                 NJD_FCD_ZER
#define FCD_ONE                 NJD_FCD_ONE
#define FCD_OC                  NJD_FCD_OC
#define FCD_IOC                 NJD_FCD_IOC
#define FCD_SA                  NJD_FCD_SA
#define FCD_ISA                 NJD_FCD_ISA
#define FCD_DA                  NJD_FCD_DA
#define FCD_IDA                 NJD_FCD_IDA
#define FCA_VC                  NJD_FCA_VC
#define FCA_AL                  NJD_FCA_AL
#define FCA_PT                  NJD_FCA_PT
#define FCA_HF                  NJD_FCA_HF
#define FCA_VF                  NJD_FCA_VF
#define FCA_HI                  NJD_FCA_HI
#define FCA_TR                  NJD_FCA_TR
#define CSPRITE_START
#define CSPRITE_END
#define CELLLISTNAME            NJS_CELL
#define CELLSTART               {
#define CELLEND                 }
#define CellTexId(_tl)          (_tl)
#define CellAttr(_attr)         (_attr)
#define CellOffset(_ox, _oy)    (_ox), (_oy)
#define CellSize(_sx, _sy)      (_sx), (_sy)
#define CellZAng(_ang)          (_ang)
#define CellPriority(_cp)       (_cp)
#define CellCenter(_cx, _cy)    (_cx), (_cy)
#define CellVColor0(_a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define CellVColor1(_a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define CellVColor2(_a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define CellVColor3(_a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define CellUV0(_u, _v)         (_u), (_v)
#define CellUV2(_u, _v)         (_u), (_v)
#define CellList                NJS_CELL
#define CellNum
#define CSPosition(_x, _y, _z)  (_x), (_y), (_z)
#define CSZAngle(_z)            _NJANG1(_z)
#define CSScale(_sx, _sy)       (_sx), (_sy)
#define CSDiffuse(_a, _r, _g, _b) _ARGB(_a, _r, _g, _b)
#define CSTREAM_START
#define CSTREAM_END
#define CELLSTREAMDATA          Sint32
#define CSTREAMSTART            {
#define CSTREAMEND              }
#define CStreamData
#define CSCurrent
#define CSTimeOffset
#define CSTimeMax
#define FCB_IA0                 NJS_FCB_IA0
#define FCB_MO1                 NJS_FCB_MO1
#define FCB_PR2                 NJS_FCB_PR2
#define FCB_CE3                 NJS_FCB_CE3
#define FCB_VC4                 NJS_FCB_VC4
#define FCB_UV5                 NJS_FCB_UV5
#define CCnk_TE(_time)          NJD_CC_TE|((_time) & 0xffff)
#define TS_L_SHIFT              16
#define TS_L_MASK               0x0fff0000
#define TS_T_MASK               0x0000ffff
#define CCnk_TS(_time, _lsize)                                       \
    (NJD_CC_TS|((_lsize)<<TS_L_SHIFT)|((_time) & TS_T_MASK))
#define CE_L_SHIFT              24
#define CE_L_MASK               0x0f000000
#define CE_EID_MASK             0x0000ffff
#define CCnk_CE(_eid, _lsize, _hbits)                                 \
    (NJD_CC_CE|(((_lsize)<<CE_L_SHIFT)&CE_L_MASK)|(_hbits)|((_eid) & CE_EID_MASK))
#define IA_T_SHIFT              16
#define IA_T_MASK               0xffff0000
#define IA_A_MASK               0x0000ffff
#define Bk_IA0(_tid, _att)                                            \
    ((((_tid) << IA_T_SHIFT) & IA_T_MASK)|((_att) & IA_A_MASK))
#define MO_Z_SHIFT              16
#define MO_Z_MASK               0xffff0000
#define MOPR_C_MASK             0x0000ffff
#define Bk_MO1(_cox, _coy, _csx, _csy, _czang)                        \
    (_cox), (_coy), (_csx), (_csy), ((_NJANG1(_czang))&MO_Z_MASK)
#define Bk_MO1PR2(_cox, _coy, _csx, _csy, _czang, _cp)                \
    (_cox), (_coy), (_csx), (_csy),                                   \
    ((((_czang)<<MO_Z_SHIFT)&MO_Z_MASK)|((_cp)&MOPR_C_MASK))
#define PR_C_MASK               0x0000ffff
#define Bk_PR2(_cp)               ((_cp)&PR_C_MASK)
#define Bk_CE3(_cx, _cy)          (_cx), (_cy)
#define Bk_VC4_0(_a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define Bk_VC4_1(_a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define Bk_VC4_2(_a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define Bk_VC4_3(_a, _r, _g, _b)  _ARGB(_a, _r, _g, _b)
#define Bk_VC5(_u0, _v0, _u2, _v2) (_u0), (_v0), (_u2), (_v2)
#define COXY(_cox, _coy)        (_cox), (_coy)
#define CSXY(_csx, _csy)        (_csx), (_csy)
#define CSUV0(_u, _v)           (_u), (_v)
#define CSUV2(_u, _v)           (_u), (_v)
#define TD_T_MASK               0x0000ffff
#define TD_A_MASK               0x0000ffff
#define TD_C_MASK               0x0000ffff
#define TD_SHIFT                16
#define TD_MASK                 0x0fff0000
#define CCnk_TD(_eid, _tid)                                           \
    (NJD_CC_TD|(((_eid)<<TD_SHIFT)&TD_MASK)|((_tid) & TD_T_MASK))
#define CCnk_AT(_eid, _att)                                           \
    (NJD_CC_AT|(((_eid)<<TD_SHIFT)&TD_MASK)|((_att) & TD_A_MASK))
#define CCnk_CZ(_eid, _cz)                                            \
    (NJD_CC_CZ|(((_eid)<<TD_SHIFT)&TD_MASK)|(short)(_NJANG1(_cz) & 0x0000ffff))
#define CCnk_CP(_eid, _cp)                                            \
    (NJD_CC_CP|(((_eid)<<TD_SHIFT)&TD_MASK)|((_cp) & TD_C_MASK))
#define AD_LS_SHIFT             16
#define AD_LS_MASK              0x0fff0000
#define AD_LA_MASK              0x0000ffff
#define ED_LS_SHIFT             24
#define ED_LS_MASK              0x0f000000
#define ED_OF_SHIFT             16
#define ED_OF_MASK              0x00ff0000
#define CBCnk_AD(_laddr, _lsize)                                       \
    (NJD_CBC_AD|(((_lsize)<<AD_LS_SHIFT)&AD_LS_MASK)|((_laddr) & AD_LS_MASK))
#define CBCnk_ED(_eid, _off, _lsize)                                   \
    ( NJD_CBC_ED|(((_lsize)<<ED_LS_SHIFT)&ED_LS_MASK)                  \
     |(((_off)<<ED_OF_SHIFT)&ED_OF_MASK) )
#define iff_NJINFO  'NJIN'
#define iff_NJCM    'NJCM'
#define iff_NJBM    'NJBM'
#define iff_NJTL    'NJTL'
#define iff_NJLI    'NJLI'
#define iff_NJCA    'NJCA'
#define iff_NMDM    'NMDM'
#define iff_NLIM    'NLIM'
#define iff_NCAM    'NCAM'
#define iff_NSSM    'NSSM'
#define iff_NJSP    'NJSP'
#define iff_NJCS    'NJCS'
#define iff_NCSM    'NCSM'
#define iff_NJAD    'NJAD'
#define iff_POF0    'POF0'
#define iff_POF1    'POF1'
#define iff_PVRT    'PVRT'
#define iff_GBIX    'GBIX'
#define iff_PVRI    'PVRI'
#define iff_PVMH    'PVMH'
#define iff_COMM    'COMM'
#define iff_CONV    'CONV'
#define iff_MDLN    'MDLN'
#define iff_IMGC    'IMGC'
#define USE_ALIGNDATA           aligndata8
#define USE_FREE_ALIGN	(0)
#define USE_02_ALIGN	(1)
#define USE_04_ALIGN	(2)
#define USE_08_ALIGN	(3)
#define USE_16_ALIGN	(4)
#define USE_32_ALIGN	(5)
#ifndef USE_MATRIX_ALIGN
#define USE_MATRIX_ALIGN 	1
#endif
#ifndef USE_LIGHT_ALIGN
#define USE_LIGHT_ALIGN 	1
#endif
#endif
