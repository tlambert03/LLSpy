from llspy.llsdir import LLSdir
from llspy.imgprocessors import ImgProcessor, ImgWriter


class ProcessPlan(object):

    def __init__(self, llsdir, imps=[], t_range=None, c_range=None):
        if not isinstance(llsdir, LLSdir):
            raise ValueError('First argument to ProcessPlan must be an LLSdir')
        assert isinstance(imps, (list, tuple)), 'imps argument must be a '\
                                                'list or tuple'
        for imp in imps:
            if not issubclass(imp[0], ImgProcessor):
                raise ValueError('imp item "{}" is not an ImgProcessor'
                                 .format(imp))
        self.llsdir = llsdir
        self.imp_classes = imps
        self.t_range, self.c_range = t_range, c_range
        self.plan()

    @property
    def ready(self):
        return hasattr(self, 'imps') and len(self.imps)

    def check_sanity(self):
        # sanity checkes go here...
        warnings = []
        if not any([isinstance(p, ImgWriter) for p, o in self.imp_classes]):
            warnings.append['No Image writer/output detected.']
        if warnings:
            raise self.PlanWarning("\n".join(warnings))

    def plan(self, skip_warnings=False):
        if not skip_warnings:
            self.check_sanity()

        errors = []
        self.imps = []  # will hold instantiated imps
        for imp_tup in self.imp_classes:
            imp, params, active = imp_tup[:3]
            try:
                self.imps.append(imp.from_llsdir(self.llsdir, **params))
            except imp.ImgProcessorError as e:
                errors.append(str(e))

        if errors:
            # FIXME: should probably only clobber broken imps, not all imps
            self.imps = []
            raise self.PlanError("\n".join(errors))

    def execute(self):
        for t in self.t_range:
            data = self.llsdir.data.asarray(t=t, c=self.c_range)
            for imp in self.imps:
                data = imp(data)

    class PlanError(Exception):
        """ hard error if the plan cannot be executed as requested """
        pass

    class PlanWarning(Exception):
        """ light error, if a plan has ill-advised steps """
        pass
