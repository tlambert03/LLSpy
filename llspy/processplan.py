from llspy.llsdir import LLSdir
from llspy.imgprocessors import ImgProcessor


class ProcessPlan(object):

    def __init__(self, llsdir, imps=[], **options):
        if not isinstance(llsdir, LLSdir):
            raise ValueError('First argument to ProcessPlan must be an LLSdir')
        assert isinstance(imps, (list, tuple)), 'imps argument must be a '\
                                                'list or tuple'
        for imp in imps:
            if not issubclass(imp, ImgProcessor):
                raise ValueError('imp item "{}" is not an ImgProcessor'
                                 .format(imp))
        self.llsdir = llsdir
        self.imp_classes = imps
        self.options = options
        self.options.update(llsdir.params)
        self.plan()

    def plan(self):
        self.imps = []
        for imp in self.imp_classes:
            if getattr(imp, 'channel_specific', False):
                pass
            if getattr(imp, 'requires_context', False):
                pass
            else:
                self.imps.append(imp(**self.options))

    def execute(self):
        pass
