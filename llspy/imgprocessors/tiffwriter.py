from . import ImgWriter
import os
from llspy.util import imsave
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError, AttributeError):
    from pathlib2 import Path


class TiffWriter(ImgWriter):
    """ Subclass of affine processor, for simplified rotation of the image in Y

    guidoc: Output Dir {datadir} = relative to data being processed
    """

    verbose_name = 'Write Tiff'
    processing_verb = 'Writing Tiff'

    def __init__(self, output_dir='{datadir}',
                 frmt='ch{c:01d}_stack{t:04d}_{w}nm.tif'):
        self.output_dir = output_dir
        self.format = frmt

    def process(self, data, meta):
        if not os.path.exists(self.output_dir):
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        nc = len(meta['c'])
        for c in range(nc):
            outpath = os.path.join(
                self.output_dir,
                self.format.format(t=meta['t'],
                                   c=meta['c'][c],
                                   w=meta['w'][c]
                                   )
            )
            imsave(data[c] if nc > 1 else data, outpath,
                   dx=meta['params'].dx, dz=meta['params'].dz,
                   dt=meta['params'].time.get('interval', 1), unit='micron')
        return data, meta

    @classmethod
    def from_llsdir(cls, llsdir, *args, **kwargs):
        if '{datadir}' in kwargs.get('output_dir', ''):
            kwargs['output_dir'] = kwargs.get('output_dir').format(
                datadir=str(llsdir.path))
        cls = cls(*args, **kwargs)
        cls.llsparams = llsdir.params
        return cls
