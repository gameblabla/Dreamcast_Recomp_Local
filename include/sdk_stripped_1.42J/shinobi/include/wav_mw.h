#ifndef	_WAV_MW_H_
#define	_WAV_MW_H_
extern	DCAIF	mwg_dcaif_wav;
#define	mwPlyInitWav(mode)			mwPlaInit(mode, &mwg_dcaif_wav)
#define	mwPlyFinishWav()			mwPlaFinish(&mwg_dcaif_wav)
#define	mwPlyCreateWav(cprm)		mwPlaCreate(cprm, &mwg_dcaif_wav)
#endif

