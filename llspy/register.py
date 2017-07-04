import os
try:
	import SimpleITK as sitk
	sitkImported = True
except Exception:
	print "could not import SimpleITK module!"
	sitkImported = False


def calcTranslationRegistration(moving, fixed):
	"""calculate the translation shift between two images"""

	fixedImage = sitk.ReadImage(fixed)
	movingImage = sitk.ReadImage(moving)
	parameterMap = sitk.GetDefaultParameterMap('translation')

	elastixImageFilter = sitk.ElastixImageFilter()
	elastixImageFilter.SetFixedImage(fixedImage)
	elastixImageFilter.SetMovingImage(movingImage)
	elastixImageFilter.SetParameterMap(parameterMap)
	elastixImageFilter.Execute()

	resultImage = elastixImageFilter.GetResultImage()
	transformParameterMap = elastixImageFilter.GetTransformParameterMap()

	return (transformParameterMap, resultImage)


def applyTranslationShift(ims, Tparams):
	"""Apply translation shift to image"""

	if not isinstance(ims, list):
		ims = [ims]

	transformixImageFilter = sitk.TransformixImageFilter()
	transformixImageFilter.SetTransformParameterMap(Tparams)

	for filename in ims:
		transformixImageFilter.SetMovingImage(sitk.ReadImage(filename))
		transformixImageFilter.Execute()
		fname = os.path.basename(filename)
		transformixImageFilter.GetResultImage()
		sitk.WriteImage(transformixImageFilter.GetResultImage(), "result_" + fname)
