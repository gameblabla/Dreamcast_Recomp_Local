#ifndef	_MPA_MW_H_
#define	_MPA_MW_H_
#define	MWD_MPA_CALC_WORK(n)		((6952) * n)
extern	DCAIF	mwg_dcaif_mpa;
#define	mwPlyInitMpa(mode)			mwPlaInit(mode, &mwg_dcaif_mpa)
#define	mwPlyFinishMpa()			mwPlaFinish(&mwg_dcaif_mpa)
#define	mwPlyCreateMpa(cprm)		mwPlaCreate(cprm, &mwg_dcaif_mpa)
#endif

