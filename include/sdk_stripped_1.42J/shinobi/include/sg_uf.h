#ifndef __SG_FLASH_H__
#define __SG_FLASH_H__
#include <sg_xpt.h>
enum {
	UFD_SAVE, UFD_LOAD, UFD_PLAY
};
enum {
	UFD_OFF,
	UFD_ON,
	UFD_UNK = 255
};
typedef enum {
	UFD_ERR_USERFLAG_PARITY_ERROR = 1,
	UFD_ERR_BANKNUMBER_ERROR,
	UFD_ERR_PROTECT_COMMON_FLAG,
	UFD_ERR_PROTECT_FLAG,
	UFD_ERR_NO_INIT,
	UFD_ERR_INIT_FAIL,
	UFD_ERR_READ_FAIL,
	UFD_ERR_WRITE_FAIL,
	UFD_ERR_NOT_FOUND,
	UFD_ERR_NO_PACKET_LEFT,
	UFD_ERR_MEMORY_FAIL,
	UFD_ERR_PERIINITFAIL,
	UFD_ERR_REFRESHFAIL,
	UFD_ERR_MAX
} UFS_ERROR;
#define UFD_PLAYHIST_PACKET0  \
	Uint8	version; 						 \
										 \
	Uint8	AutoSave; 						 \
										 \
	Uint8	ProdNum[10]; 						 \
										 \
	Uint8	ProdName[48];
#define UFD_PLAYHIST_PACKET1  \
	Uint8	ProdName2[44];						 \
										 \
	Uint32	Kind;							 \
										 \
	Uint32	FirstStartTime;						 \
										 \
	Uint16	CRC;							 \
										 \
	Uint8	PeriIdx[6];
#define UFD_PLAYHIST_PACKET2  \
	Uint32	PrevStartTime;						 \
										 \
	Uint16	StartCount;						 \
										 \
	Uint16	PlayTime[24];						 \
										 \
	Uint16	LoadCount;						 \
										 \
	Uint32	Reserve_2;
#define UFD_PLAYHIST_PACKET3  \
	Uint16	SaveCount;						 \
										 \
	Uint8	GameEst;						 \
										 \
	Uint8	GameCarry;						 \
										 \
	Uint32	FirstNetPlay;						 \
										 \
	Uint32	PrevNetPlay;						 \
										 \
	Uint16	NetPlayCount;						 \
										 \
	Uint16	NetPlayTotalTime;					 \
										 \
	Uint8	FreeArea[32];						 \
										 \
	Uint8	Reserved2[10];						 \
										 \
	Uint16	SaveOccur;
#define	UFD_WORK1_SIZ	65536
#define	UFD_WORK2_SIZ	60
#define UFD_WORK3_SIZ	65536
#define UFD_WORK4_SIZ	32768
#define	UFD_REQUIRED_REST_PACKET	2
#define UFD_WORK_NOCHANGE	((void *)-1)
typedef struct tagUFS_Packet0 {
	UFD_PLAYHIST_PACKET0
} UFS_HistoryPacket0;
typedef struct tag_HistoryPacket1 {
	UFD_PLAYHIST_PACKET1
} UFS_HistoryPacket1;
typedef struct tagUFS_HistoryPacket2 {
	UFD_PLAYHIST_PACKET2
} UFS_HistoryPacket2;
typedef struct tagUFS_HistoryPacket3 {
	UFD_PLAYHIST_PACKET3
} UFS_HistoryPacket3;
typedef struct tagUFS_PlayHistory {
	UFS_HistoryPacket0	packet0;
	UFS_HistoryPacket1	packet1;
	UFS_HistoryPacket2	packet2;
	UFS_HistoryPacket3	packet3;
} UFS_PlayHistory;
typedef struct tagUFS_AllPlayHistory {
	UFD_PLAYHIST_PACKET0
	UFD_PLAYHIST_PACKET1
	UFD_PLAYHIST_PACKET2
	UFD_PLAYHIST_PACKET3
} UFS_AllPlayHistory;
extern UFS_ERROR ufgErrno;
Bool ufInitSystem(void* work1, void* work2, void* work3, void* work4);
Bool ufChangeWorkBuffer(void* work1, void* work2, void* work3, void* work4);
Sint32 ufPlayTime(Uint8 mode, Uint8 est, Uint8 carry, Uint8 param[32]);
Bool ufSynch(void);
Bool ufAutoSynch(Uint32 count);
Bool ufReadAllProduct(Uint8* Buffer);
Bool ufReadAllHead(Uint8* ProdNum, UFS_AllPlayHistory* buff);
Bool ufTitleDelete(void);
Bool ufChangeAutoSave(Uint8 Flag);
Bool ufConnect(Uint32 time);
Bool ufDisConnect(void);
Bool ufSafeRefresh(void);
Bool ufGetControllerList(Uint32* list);
Bool ufGetExtControllerList(Uint32* list);
void ufExitSystem(void);
#endif
