try:
    import llspy
except ImportError:
    import os
    import sys

    thisDirectory = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisDirectory, os.pardir, os.pardir))
    import llspy

import logging
import os
import shutil
import sys

import click
import voluptuous

from llspy import exceptions, libinstall, llsdir, otf, schema, util

if "--debug" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("llspy.CLI")

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

DEFAULTS = schema.__defaults__

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


class Config(dict):
    def __init__(self):
        # default path is based on click.get_app_dir
        self.default_path = os.path.join(click.get_app_dir("LLSpy"), "config.ini")
        self.comment = "# "

        super().__init__()
        # intialize dict with defaults from schema.py
        for k, v in schema.__defaults__.items():
            self[k] = v[0]
        if os.path.exists(self.default_path):
            self.read_config(self.default_path)

    def read_config(self, filename):
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read([filename])
        try:
            for s in parser.sections():
                section = parser._sections[s]
                for key, val in section.items():
                    if key in ("MIP", "rMIP", "trimZ", "trimY", "trimX"):
                        from ast import literal_eval as make_tuple

                        section[key] = make_tuple(val)
                self.update(section)
        except configparser.NoSectionError:
            pass

    def create_new_cfgfile(self):
        if not os.path.isdir(os.path.dirname(self.default_path)):
            os.makedirs(os.path.dirname(self.default_path))
        if not os.path.isfile(self.default_path):
            with open(self.default_path, "a") as cfgfile:
                cfgfile.write("[General]")

    def delete_cfgfile(self):
        if os.path.isfile(self.default_path):
            os.remove(self.default_path)
            try:
                os.rmdir(os.path.dirname(self.default_path))
            except Exception:
                pass

    def print_cfgfile(self):
        if os.path.isfile(self.default_path):
            click.secho(
                "\nConfig PATH: %s" % click.format_filename(self.default_path),
                fg="cyan",
            )
            with open(self.default_path) as f:
                for line in f:
                    if line.startswith("["):
                        click.secho(line, nl=False, underline=True)
                    if (
                        line.startswith("# ")
                        or line.startswith("; ")
                        or line.startswith(self.comment)
                    ):
                        click.secho(line, fg="red", nl=False, dim=True)
                    elif "=" in line:
                        splt = line.split("=")
                        click.secho(splt[0], nl=False, fg="magenta", bold=True)
                        click.echo("=", nl=False)
                        click.secho(splt[1], fg="yellow", nl=False)
                click.echo()
        else:
            click.echo(
                "No config file found at: %s" % click.format_filename(self.default_path)
            )

    def update_default(self, key, value):
        if key not in DEFAULTS:
            click.secho(
                f"{key} is not a recognized parameter! use config --info to "
                "list all recognized parameters",
                fg="red",
            )
            return 0
        try:
            key, value = next(iter(schema.validateItems(**{key: value}).items()))
        except Exception as e:
            click.secho(str(e), fg="red")
            return 0

        if not os.path.isfile(self.default_path):
            self.create_new_cfgfile()

        # preserve comments
        with open(self.default_path) as f:
            comments = [
                x for x in list(f) if x.startswith(self.comment) and key not in x
            ]

        parser = configparser.ConfigParser(allow_no_value=True)
        parser.optionxform = str
        parser.read(self.default_path)
        parser["General"][key] = str(value)
        with open(self.default_path, "w") as configfile:
            parser.write(configfile)
            if len(comments):
                [configfile.write(c) for c in comments]

    def remove_key(self, key, section="General"):
        if not os.path.isfile(self.default_path):
            self.create_new_cfgfile()

        parser = configparser.ConfigParser(allow_no_value=True)
        parser.optionxform = str
        parser.read(self.default_path)
        parser.remove_option(section, key)
        with open(self.default_path, "w") as configfile:
            parser.write(configfile)

    def disable_key(self, key, section="General"):
        if not os.path.isfile(self.default_path):
            return 0
        with open(self.default_path, "r+") as f:
            text = f.read()
            f.seek(0)  # rewind
            if key in text and self.comment + key not in text:
                text = text.replace(key, self.comment + key)
            f.write(text)

    def enable_key(self, key, section="General"):
        if not os.path.isfile(self.default_path):
            return 0
        with open(self.default_path, "r+") as f:
            lines = f.readlines()
            f.seek(0)  # rewind
            for i, line in enumerate(lines):
                if key == "ALL":
                    if line.startswith(self.comment):
                        lines[i] = line.replace(self.comment, "")
                else:
                    if key in line and line.startswith(self.comment):
                        lines[i] = line.replace(self.comment, "")
            [f.write(line) for line in lines]
            f.truncate()


pass_config = click.make_pass_decorator(Config, ensure=True)


def read_config(ctx, param, value):
    """Callback that is used whenever --config is passed.  We use this to
    always load the correct config.  This means that the config is loaded
    even if the group itself never executes so our aliases stay always
    available.
    """
    cfg = ctx.ensure_object(Config)
    for v in value:
        cfg.read_config(v)
    return value


def exclusive(ctx_params, exclusive_params, error_message):
    if sum(1 if ctx_params[p] else 0 for p in exclusive_params) > 1:
        raise click.UsageError(error_message)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=llspy.__version__, prog_name="LLSpy")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    callback=read_config,
    expose_value=False,
    multiple=True,
    help="Config file to use instead of the system config.",
)
@click.option("--debug", is_flag=True, expose_value=False)
def cli():
    """LLSpy

    This is the command line interface for the LLSpy library, to facilitate
    processing of lattice light sheet data using cudaDeconv and other tools.
    """


@cli.command()
@click.argument(
    "paths",
    metavar="LLSDIR",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option("--showsize/--hidesize", "-s/-h", "showsize", is_flag=True, default=True)
@click.option("--recurse", "-r", is_flag=True)
@click.option("--depth", "-d", type=int, default=1)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity with additional -v flags, e.g. -vv",
)
def info(paths, verbose, recurse, depth, showsize):
    """Get info on an LLSDIR.  Change verbosity with -v"""
    logging.getLogger("llspy.llsdir").setLevel("CRITICAL")
    paths = list(paths)

    if recurse:
        depth = 1000

    for i, path in enumerate(paths):
        if not util.pathHasPattern(path, pattern="*Settings.txt"):
            paths.pop(i)
            subf = sorted(util.get_subfolders_containing_filepattern(path, level=depth))
            [paths.insert(i, s) for s in reversed(subf)]

    # remove duplicates
    paths = sorted(set(paths))

    if verbose == 0 and len(paths):
        click.echo()
        headers = ["Path", "nC", "nT", "nZ", "nY", "nX", "Angle", "dZ", "dXY", "compr"]
        maxPathLen = max(len(util.shortname(str(p), 3)) for p in paths) + 2
        row_format = "{:<%d}{:<4}{:<5}{:<5}{:<6}{:<6}{:<7}{:<7}{:<7}{:<5}" % maxPathLen
        if showsize:
            headers.append("size")
            row_format = row_format + "{:>7}"
        click.secho(
            row_format.format(*(str(i) for i in headers)),
            underline=True,
            fg="cyan",
            bold=True,
        )
        row_format = "{:<4}{:<5}{:<5}{:<6}{:<6}{:<7}{:<7}{:<7}{:<5}"
        if showsize:
            row_format = row_format + "{:>7}"
        for path in paths:
            try:
                E = llsdir.LLSdir(path)
                infolist = [
                    E.parameters.nc,
                    E.parameters.nt,
                    E.parameters.nz,
                    E.parameters.ny,
                    E.parameters.nx,
                    f"{E.parameters.angle:2.1f}" if E.parameters.samplescan else "0",
                    f"{E.parameters.dz:0.3f}",
                    f"{E.parameters.dx:0.3f}",
                    "Yes" if E.is_compressed() else "No",
                ]
                if showsize:
                    foldersize = util.getfoldersize(path, recurse=True)
                    infolist.append(util.format_size(foldersize))
                f = "{:<%d}" % maxPathLen
                short = f.format(util.shortname(str(E.path), 3))
                click.secho(
                    os.path.split(short)[0] + os.path.sep,
                    nl=False,
                    fg="magenta",
                    bold=False,
                )
                click.secho(os.path.split(short)[1], nl=False, fg="yellow", bold=True)
                click.echo(row_format.format(*(i for i in infolist)))
            except exceptions.LLSpyError:
                pass
    click.echo()


def check_iters(ctx, param, value):
    if value == 0:
        click.echo(
            "You've selected iters=0 ... if you don't need deconvolution, "
            "use the deskew command"
        )
        ctx.exit()
    elif value > 0:
        cfg = ctx.ensure_object(Config)
        fail = False
        if not (ctx.params["otfDir"] or cfg["otfDir"]):
            click.secho(
                "\nDeconvolution requested, but no OTF directory provided!",
                bold=True,
                fg="red",
            )
            fail = True

        otfdir = None
        if ctx.params["otfDir"] is not None:
            otfdir = ctx.params["otfDir"]
        elif cfg["otfDir"] is not None:
            otfdir = cfg["otfDir"]

        if otfdir is not None and not otf.dir_has_otfs(otfdir):
            click.secho(
                "\nOTF directory has no OTFs! -> %s" % otfdir, bold=True, fg="red"
            )
            fail = True

        if fail:
            click.echo("use ", nl=False)
            click.secho("--otfDir PATH", bold=True, nl=False, fg="cyan")
            click.echo(" to specify a directory, during deconvolution")
            click.echo("or use ", nl=False)
            click.secho("lls config --set otfDir PATH ", bold=True, nl=False, fg="cyan")
            click.echo("to set a directory in the configuration\n")
            ctx.exit()
    return value


@cli.command()
@click.argument(
    "path",
    metavar="LLSDIR",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    callback=read_config,
    expose_value=False,
    multiple=True,
    is_eager=True,
    help="Overwrite defaults with values in specified file.",
)
@click.option(
    "--otfDir",
    "otfDir",
    is_eager=True,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Directory with otfs. OTFs should be named (e.g.): 488_otf.tif",
)
@click.option(
    "-b",
    "--background",
    metavar="INT",
    type=click.IntRange(min=-1, max=20000),
    help="Background to subtract. -1 = autodetect.",
    default=DEFAULTS["background"][0],
    show_default=True,
)
@click.option(
    "-i",
    "--iters",
    "nIters",
    default=DEFAULTS["nIters"][0],
    show_default=True,
    metavar="[INT: 0-30]",
    type=click.IntRange(min=0, max=30),
    callback=check_iters,
    help="Number of RL-deconvolution iterations",
)
@click.option(
    "-R",
    "--rotate",
    "bRotate",
    is_flag=True,
    help="rotate image to coverslip coordinates after deconvolution",
    default=DEFAULTS["bRotate"][0],
    show_default=True,
)
@click.option(
    "-S",
    "--saveDeskewed",
    "saveDeskewedRaw",
    is_flag=True,
    help="Save raw deskwed files, in addition to deconvolved.",
    default=DEFAULTS["saveDeskewedRaw"][0],
    show_default=True,
)
@click.option(
    "--cropPad",
    "cropPad",
    metavar="INT",
    default=DEFAULTS["cropPad"][0],
    show_default=True,
    help="additional edge pixels to keep when autocropping",
)
@click.option(
    "-w",
    "--width",
    metavar="[INT: 0-3000]",
    type=click.IntRange(min=0, max=3000),
    help="Width of image after deskewing. 0 = full frame."
    "[default: autocrop based on image content]",
)
@click.option(
    "-s",
    "--shift",
    metavar="[INT: -1500-1500]",
    type=click.IntRange(min=-1500, max=1500),
    help="Shift center when cropping",
    default=DEFAULTS["shift"][0],
    show_default=True,
)
@click.option(
    "-m",
    "--rMIP",
    "rMIP",
    default=DEFAULTS["rMIP"][0],
    show_default=True,
    metavar="<BOOL BOOL BOOL>",
    nargs=3,
    type=int,
    help="Save max-intensity projection after deskewing "
    "along x, y, or z axis.  Takes 3 binary numbers separated by spaces.",
)
@click.option(
    "-M",
    "--MIP",
    "MIP",
    default=DEFAULTS["MIP"][0],
    show_default=True,
    metavar="<BOOL BOOL BOOL>",
    nargs=3,
    type=int,
    help="Save max-intensity projection after deconvolution along x, "
    "y, or z axis. Takes 3 binary numbers separated by spaces",
)
@click.option(
    "--mergemips/--sepmips",
    "mergeMIPs",
    help="Combine MIP files into single hyperstack (or not).",
    default=DEFAULTS["mergeMIPs"][0],
    show_default=True,
)
@click.option(
    "--uint16/--uint32",
    is_flag=True,
    help="Save results as 16 (default) or 32- bit",
    default=DEFAULTS["uint16"][0],
)
@click.option(
    "-p",
    "--bleachCorrect",
    "bleachCorrection",
    is_flag=True,
    help="Perform bleach correction on timelapse data",
    default=DEFAULTS["bleachCorrection"][0],
    show_default=True,
)
@click.option(
    "--trimX",
    "trimX",
    default=DEFAULTS["trimX"][0],
    show_default=True,
    metavar="<LEFT RIGHT>",
    nargs=2,
    type=int,
    help="Number of X pixels to trim off raw data before processing. "
    "Takes 2 integers separated by spaces",
)
@click.option(
    "--trimY",
    "trimY",
    default=DEFAULTS["trimY"][0],
    show_default=True,
    metavar="<TOP BOT>",
    nargs=2,
    type=int,
    help="Number of Y pixels to trim off raw data before processing. "
    "Takes 2 integers separated by spaces",
)
@click.option(
    "--trimZ",
    "trimZ",
    default=DEFAULTS["trimZ"][0],
    show_default=True,
    metavar="<FIRST LAST>",
    nargs=2,
    type=int,
    help="Number of Z pixels to trim off raw data before processing. "
    "Takes 2 integers separated by spaces",
)
@click.option(
    "-f",
    "--correctFlash",
    "correctFlash",
    is_flag=True,
    type=click.BOOL,
    help="Correct Flash pixels before processing.",
    default=DEFAULTS["correctFlash"][0],
    show_default=True,
)
@click.option(
    "-F",
    "--medianFilter",
    "medianFilter",
    is_flag=True,
    help="Correct raw data with selective median filter. "
    "Note: this occurs after flash correction (if requested).",
    default=DEFAULTS["medianFilter"][0],
    show_default=True,
)
@click.option(
    "--keepCorrected",
    "keepCorrected",
    is_flag=True,
    default=False,
    help="Process even if the folder already has a processingLog JSON file, "
    "(otherwise skip)",
)
@click.option(
    "-z",
    "--compress",
    "compressRaw",
    is_flag=True,
    default=DEFAULTS["compressRaw"][0],
    show_default=True,
    help="Compress raw files after processing",
)
@click.option(
    "-r",
    "--reprocess",
    "reprocess",
    is_flag=True,
    default=None,
    help="Process even if the folder already has a processingLog JSON file, "
    "(otherwise skip)",
)
@click.option(
    "--batch",
    is_flag=True,
    default=None,
    help="batch process folder: Recurse through all subfolders with a "
    "Settings.txt file",
)
@click.option(
    "--yes/--no",
    "useAlreadyCorrected",
    is_flag=True,
    default=None,
    help="autorespond to prompts",
)
@pass_config
def decon(config, path, **kwargs):
    """Deskew and deconvolve data in LLSDIR."""
    # update config with relevant values from

    # raw deskewed MIPs imply saving Deskewed Raw files
    if any(kwargs["rMIP"]):
        kwargs["saveDeskewedRaw"] = True

    # override config with keyword options
    for key, value in kwargs.items():
        if key in config and value is not None:
            config[key] = value

    # batch processing
    if not kwargs["batch"] and not util.pathHasPattern(path):
        click.secho(
            "not a LLS data folder with *Settings.txt!\n"
            "use --batch for batch processing",
            fg="red",
        )
        sys.exit(1)

    # # allow for provided OTF directory
    # if not default_otfdir and options.otfdir is None:
    #     print('Could not find OTF directory at {}'.format(default_otfdir))
    #     sys.exit('Please specify where the OTFs are with --otfdir')
    # elif options.otfdir is None:
    #     options.otfdir = default_otfdir

    def procfolder(dirpath, options):
        E = llsdir.LLSdir(dirpath)

        # check whether folder has already been processed by the presence of a
        # ProcessingLog.txt file
        if E.has_been_processed() and not options["reprocess"]:
            print(f"Folder already appears to be processed: {E.path}")
            print("Skipping ... use the '--reprocess' flag to force reprocessing")
            return 0

        if options["reprocess"] and E.is_compressed():
            # uncompress the raw files first...
            E.decompress()
            # if reprocessing, look for a top level MIPs folder and remove it
            if E.path.joinpath("MIPs").exists():
                shutil.rmtree(E.path.joinpath("MIPs"))

        click.secho(
            "\n" + "#" * (int(len(str(E.path))) + 24) + "\n##    ", fg="cyan", nl=False
        )
        click.secho("processing: %s    " % str(E.path), fg="yellow", nl=False)
        click.secho("##\n" + "#" * (int(len(str(E.path))) + 24) + "\n", fg="cyan")

        if options["correctFlash"]:
            if E.is_corrected():
                if kwargs["useAlreadyCorrected"] is None:
                    import select

                    click.echo(
                        "Corrected folder already exists!  Use it? [y/N]", nl=False
                    )
                    click.secho(" (6 seconds to answer)", blink=True)
                    i, o, e = select.select([sys.stdin], [], [], 6)
                    if i:
                        useCor = sys.stdin.readline().strip()[0].lower() == "y"
                    else:
                        useCor = False
                        click.echo("timed out...")
                elif kwargs["useAlreadyCorrected"]:
                    useCor = True
                else:
                    useCor = False

                if useCor:
                    click.echo("Using already corrected files...")
                    options["correctFlash"] = False
                    E.path = E.path.joinpath("Corrected")
                else:
                    click.echo("recreating corrected files...")

        try:
            # try:
            E.autoprocess(**options)
            # logdict = None
            # except Exception as e:
            #     raise click.ClickException(e)
        except Exception:
            raise

    if kwargs["batch"]:
        try:
            subfolders = util.get_subfolders_containing_filepattern(
                path, filepattern="*Settings.txt"
            )
            click.secho("found the following LLS data folders:", fg="magenta")
            for folder in subfolders:
                click.secho(folder.split(path)[1], fg="yellow")
            for folder in subfolders:
                try:
                    procfolder(folder, config)
                except voluptuous.error.MultipleInvalid as e:
                    e = str(e).replace("@ data['", "for ")
                    e = e.strip("'][0]")
                    click.secho("VALIDATION ERROR: %s" % e, fg="red")
                except exceptions.LLSpyError as e:
                    click.secho("ERROR: %s" % e, fg="red")
            click.echo("\n\nDone batch processing!")
            sys.exit(0)
        except Exception:
            raise
    else:
        try:
            procfolder(path, config)
            click.echo("Done!")
            sys.exit(0)
        except voluptuous.error.MultipleInvalid as e:
            e = str(e).replace("@ data['", "for ")
            e = e.strip("'][0]")
            click.secho("VALIDATION ERROR: %s" % e, fg="red")
        except exceptions.LLSpyError as e:
            click.secho("ERROR: %s" % e, fg="red")

    sys.exit(0)


@cli.command()
def deskew():
    """Deskewing only (no decon) of LLS data"""
    print("Not yet implemented")


@cli.command()
@click.option(
    "-t",
    "--test",
    "_test",
    is_flag=True,
    default=False,
    help="just open window and close",
)
def gui(_test):
    """Launch LLSpy Graphical User Interface"""
    from llspy.bin.llspy_gui import main, test

    if _test:
        exceptionHandler = llspy.gui.exceptions.ExceptionHandler()
        sys.excepthook = exceptionHandler.handler
        # exceptionHandler.errorMessage.connect(mainGUI.show_error_window)
        test()
    else:
        main()


@cli.command()
def slm():
    """Launch LLSpy Graphical User Interface"""
    from slmgen.slmwindow import main

    main()


@cli.command()
def reg():
    """Channel registration"""
    print("Not yet implemented")


@cli.command()
@click.option(
    "-c",
    "--calibrate",
    metavar="DATADIR",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Generate camera calibration file from data in DATADIR",
)
def camera(calibrate):
    """Camera correction calibration"""

    if calibrate is not None:
        import glob

        import tifffile as tf

        from llspy import camcalib

        darklist = glob.glob(os.path.join(calibrate, "*dark*.tif"))
        numdark = len(darklist)
        with click.progressbar(length=numdark * 2, label="Loading dark images") as bar:
            darkavg, darkstd = camcalib.process_dark_images(calibrate, bar.update)

        with tf.TiffFile(darklist[0]) as t:
            nz, ny, nx = t.series[0].shape

        with click.progressbar(length=ny * nx, label="Processing bright images") as bar:
            camcalib.process_bright_images(calibrate, darkavg, darkstd, bar.update)
        click.secho(
            f"Done! Calibration file has been written to: {calibrate}",
            bold=True,
            fg="yellow",
        )


@cli.command()
@click.argument(
    "paths",
    metavar="LLSDIR",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "-r",
    "--reduce",
    "_reduce",
    is_flag=True,
    default=False,
    help="Delete all processed data, returning data folder to post-acquisition state",
)
@click.option(
    "-f",
    "--freeze",
    is_flag=True,
    default=False,
    help="Delete all processed data and compress raw data",
)
@click.option(
    "-d",
    "--decompress",
    is_flag=True,
    default=False,
    help="Decompress folder if already compress.",
)
@click.option(
    "--keepmips/--removemips",
    "keepmips",
    help="Keep MIPs (as preview) when reducing to raw or freezing.",
    default=True,
    show_default=True,
)
@click.option(
    "--recurse",
    is_flag=True,
    default=False,
    help="Recurse through subdirectories (use --depth to limit "
    "recursion depth or --age to set minimum experiment age)",
    show_default=True,
)
@click.option(
    "--depth", type=int, default=1, help="recursion depth (used with --recurse)"
)
@click.option(
    "-n",
    "--dryrun",
    is_flag=True,
    default=False,
    help="test run only, nothing performed",
)
@click.option(
    "-a",
    "--age",
    "minage",
    default=0,
    help="Minimum age (days) of LLSdir to act on",
    show_default=True,
)
def compress(
    paths, freeze, _reduce, decompress, recurse, minage, keepmips, depth, dryrun
):
    """Compression & decompression of LLSdir"""
    exclusive(
        click.get_current_context().params,
        ["freeze", "_reduce", "decompress"],
        "options {freeze, reduce, decompress} are mutually exclusive",
    )

    logging.getLogger("llspy.llsdir").setLevel("CRITICAL")
    paths = list(paths)

    if recurse:
        depth = 1000

    # recurse and restrict to LLSdirs
    for i, path in enumerate(paths):
        if not util.pathHasPattern(path, pattern="*Settings.txt"):
            paths.pop(i)
            subf = sorted(util.get_subfolders_containing_filepattern(path, level=depth))
            [paths.insert(i, s) for s in reversed(subf)]

    # remove duplicates
    paths = sorted(set(paths))

    if dryrun:
        click.secho("DRY RUN: NOTHING PERFORMED!", fg="red", underline=True)

    for path in paths:
        try:
            E = llsdir.LLSdir(path)
            if E.age < minage:
                click.secho("      skip:", nl=False, underline=False, fg="blue")
                click.secho(f"{path} ({E.age} days old)", fg="blue")
                continue
            if decompress:
                click.secho("decompress:", nl=False, underline=False, fg="yellow")
                click.echo(f"{path}")
                if not dryrun:
                    E.decompress()
                continue
            elif _reduce:
                click.secho("    reduce:", nl=False, underline=False, fg="yellow")
                click.echo(f"{path}")
                if not dryrun:
                    E.reduce_to_raw(keepmip=keepmips)
                continue
            else:
                if freeze:
                    click.secho("    freeze:", nl=False, underline=False, fg="yellow")
                    click.echo(f"{path}")
                    if not dryrun:
                        E.freeze(keepmip=keepmips)
                else:
                    click.secho("  compress:", nl=False, underline=False, fg="yellow")
                    click.echo(f"{path}")
                    if not dryrun:
                        E.compress()
        except exceptions.CompressionError as e:
            logger.warning(e)


@cli.command()
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="Delete all files created by LLSpy and LLSpyGUI",
)
@click.option(
    "-c",
    "--config",
    "configfile",
    is_flag=True,
    default=False,
    help="Delete config files created by LLSpy and LLSpyGUI",
)
@click.option(
    "-l",
    "--logs",
    is_flag=True,
    default=False,
    help="Delete log files created by LLSpy and LLSpyGUI",
)
@pass_config
def clean(config, all, configfile, logs):
    """Delete LLSpy logs and preferences"""
    appdir = os.path.dirname(config.default_path)
    if all:
        try:
            shutil.rmtree(appdir)
            click.echo("removed ", appdir)
        except Exception:
            pass
        return
    if config:
        try:
            os.remove(config.default_path)
            click.echo("removed ", config.default_path)
        except Exception:
            pass
    if logs:
        try:
            for f in os.listdir(appdir):
                if ".log" in f:
                    os.remove(os.path.join(appdir, f))
                    click.echo("removed ", os.path.join(appdir, f))
        except Exception:
            pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, resolve_path=True))
@click.option(
    "-z",
    "--stack",
    "stack",
    is_flag=True,
    default=False,
    help="Show Z stack from first timepoint (otherwise look for MIP)",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    callback=read_config,
    expose_value=False,
    multiple=True,
    is_eager=True,
    help="Overwrite defaults with values in specified file.",
)
@click.option("-t", "--timepoint", type=int, default=0)
@pass_config
def show(config, path, stack, timepoint):
    """Preview MIPS or single Z stack from LLSdir"""
    import numpy as np
    from qtpy import QtWidgets

    from llspy.gui.img_dialog import ImgDialog

    logging.getLogger("llspy.llsdir").setLevel("CRITICAL")
    APP = QtWidgets.QApplication(sys.argv)

    # if the path provided is a tiff, just show it
    if os.path.isfile(path) and path.endswith(".tif"):
        data = util.imread(path)
    if os.path.isdir(path) and util.pathHasPattern(path, "*Settings.txt"):
        try:
            data = None
            exp = llsdir.LLSdir(path)
            # unless z-stack was requested, look for mips
            if not stack:
                # look for decon first, then deskewed
                if exp.path.joinpath("GPUdecon").joinpath("MIPs").exists():
                    path = exp.path.joinpath("GPUdecon").joinpath("MIPs")
                    zmip = util.find_filepattern(path, "*comboMIP_z.tif")
                    data = util.imread(zmip)
                    nt, ny, nx = data.shape
                    data = np.reshape(data, (nt, 1, 1, ny, nx))
                elif exp.path.joinpath("Deskewed").joinpath("MIPs").exists():
                    path = exp.path.joinpath("Deskewed").joinpath("MIPs")
                    zmip = util.find_filepattern(path, "*comboMIP_z.tif")
                    data = util.imread(zmip)
                    nt, ny, nx = data.shape
                    data = np.reshape(data, (nt, 1, 1, ny, nx))

            if data is None:
                data = exp.preview(tR=timepoint, **config)
                config = exp.localParams()

        except exceptions.ParametersError as e:
            click.secho(str(e), fg="red")
            click.echo('Try setting missing parameters using "lls config"')
            return
    dialog = ImgDialog(data, info=config)
    dialog.show()
    sys.exit(APP.exec_())


@cli.command(short_help="Install cudaDeconv libraries and binaries")
@click.argument("path", type=click.Path(exists=True, file_okay=True, resolve_path=True))
@click.option(
    "-n",
    "--dryrun",
    is_flag=True,
    default=False,
    help="Just show what files would be moved to where",
)
def install(path, dryrun):
    """Install cudaDeconv libraries and binaries to LLSPY.

    Provided PATH argument can be a LIB or BIN directory, or a parent
    directory that contains both the LIB and BIN directories.  The appropriate
    library and binary files will be installed to the LLSpy installation.

    """
    if os.environ.get("CONDA_DEFAULT_ENV", "") in ("root", "base"):
        if not click.confirm(
            "It looks like you're in the root conda environment... "
            "It is recommended that you install llspy in its own environment.\n"
            "Continue?"
        ):
            return
    libinstall.install(path, dryrun)


def del_sysconfig(ctx, param, value):
    if value:
        if click.confirm("Are you sure you want to clear the configuration?"):
            cfg = ctx.ensure_object(Config)
            cfg.delete_cfgfile()
            ctx.exit()


def print_info(ctx, param, value):
    if value:
        schema.printOptions()
        ctx.exit()


def edit_sysconfig(ctx, param, value):
    if value:
        cfg = ctx.ensure_object(Config)
        click.edit(filename=cfg.default_path)


@cli.command()
@click.option(
    "-s",
    "--set",
    "_set",
    metavar="KEY VALUE",
    nargs=2,
    multiple=True,
    help="Set KEY to VALUE in config",
)
@click.option(
    "-r", "--remove", metavar="KEY", multiple=True, help="Remove KEY in config"
)
@click.option("--disable", metavar="KEY", multiple=True, help="Disable KEY in config")
@click.option(
    "--enable",
    metavar="KEY",
    multiple=True,
    help='Enable KEY in config (if disabled). Use "--enable ALL" to '
    "enable all disabled keys.",
)
@click.option(
    "-e",
    "--edit",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=edit_sysconfig,
    default=False,
    help="Directly edit system LLSpy configuration",
)
@click.option(
    "-p",
    "--print",
    "_print",
    is_flag=True,
    default=False,
    help="Print current system LLSpy configuration",
)
@click.option(
    "-i",
    "--info",
    is_flag=True,
    callback=print_info,
    is_eager=True,
    expose_value=False,
    default=False,
    help="Print info on all possible settings and quit",
)
@click.option(
    "--delete",
    is_flag=True,
    callback=del_sysconfig,
    is_eager=True,
    expose_value=False,
    default=False,
    help="Delete system configuration for LLSpy and exit",
)
@pass_config
def config(config, _set, remove, disable, enable, _print):
    """Manipulate the system configuration for LLSpy"""
    for key, value in _set:
        if key in ("MIP", "rMIP", "trimZ", "trimY", "trimX"):
            from ast import literal_eval as make_tuple

            value = make_tuple(value)
        config.update_default(key, value)
    [config.remove_key(key) for key in remove]
    [config.enable_key(key) for key in enable]
    [config.disable_key(key) for key in disable]
    if _print:
        config.print_cfgfile()


if __name__ == "__main__":
    cli()
