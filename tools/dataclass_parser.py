# pylint: disable=redefined-builtin
# pyright: reportUnreachable=false
"""
Light weight argparser from a dataclass.

There are some libraries out there that mostly do what we want, but none are quite right.


Took motivation from the following:
https://github.com/typed-argparse/typed-argparse
https://github.com/SunDoge/typed-args
https://github.com/rmorshea/noxopt


To get a parser use something like:

from typing import TypeAlias
RUN_TYPE: TypeAlias = list[list[str]] | None


@dataclass
class Example(DataclassParser):
    cmd: list[Literal['a','b']] | None = add_option("-c", "--cmd")
    run: Annotated[list[list[str]] | None, Option(help='hello')] = add_option("-r", "--run")
    another: Annotated[list[list[str]] | None, option("-a", "--another", help='hello')] = None

    other: RUN_TYPE = add_option(help="hello")
    version: str | None = None
    lock: bool = False
    no_cov: bool = False

"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import (
    dataclass,
    field,
    fields,
    is_dataclass,
    replace,
)
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Union,  # pyright: ignore[reportDeprecated]
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    import sys
    from collections.abc import Callable, Container, Sequence

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


_NoneType = type(None)

UNDEFINED = cast(
    "Any",
    type("Undefined", (), {"__repr__": lambda self: "UNDEFINED"})(),  # pyright: ignore[reportUnknownLambdaType]  # noqa: ARG005
)


@dataclass
class Option:
    """Class to handle options."""

    flags: Sequence[str] = UNDEFINED
    # remainder are alphabetical
    action: str | None = UNDEFINED
    choices: Container[Any] = UNDEFINED
    const: Any = UNDEFINED
    default: Any | None = UNDEFINED
    dest: str = UNDEFINED
    help: str = UNDEFINED
    metavar: str = UNDEFINED
    nargs: str | int | None = UNDEFINED
    required: bool = UNDEFINED
    type: int | float | Callable[[Any], Any] = UNDEFINED
    prefix_char: str = "-"

    def __post_init__(self) -> None:
        if isinstance(self.flags, str):
            self.flags = (self.flags,)
        if self.flags is not UNDEFINED:
            for f in self.flags:
                if not f.startswith(self.prefix_char):
                    msg = f"Option only supports flags, but got {f!r}"
                    raise ValueError(msg)

    def asdict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            k: v
            for k, v in (
                # Can't use asdict() since that deep copies and we need
                # to filter using an identity check against UNDEFINED.
                [
                    (f.name, getattr(self, f.name))
                    for f in fields(self)
                    if f.name != "prefix_char"
                ]
            )
            if v is not UNDEFINED
        }

    def add_argument_to_parser(
        self,
        parser: ArgumentParser,
        prefix_char: str = "-",
    ) -> None:
        """Add argument to parser."""
        kwargs = self.asdict()

        flags = kwargs.pop("flags")

        # make sure flags have correct prefixing:
        if not all(flag.startswith(prefix_char) for flag in flags):
            new_flags: list[str] = []
            for flag in flags:
                if flag.startswith(prefix_char):
                    new_flags.append(flag)
                elif flag.startswith("--"):
                    new_flags.append(prefix_char * 2 + flag.lstrip("-"))
                elif flag.startswith("-"):
                    new_flags.append(prefix_char + flag.lstrip("-"))
                else:
                    msg = f"bad flag {flag} prefix_char {prefix_char}"
                    raise ValueError(msg)

            flags = new_flags

        _ = parser.add_argument(*flags, **kwargs)

    @classmethod
    def factory(
        cls,
        *flags: str,
        action: str | None = UNDEFINED,
        choices: Container[Any] = UNDEFINED,
        const: Any = UNDEFINED,
        default: Any | None = UNDEFINED,
        dest: str = UNDEFINED,
        help: str = UNDEFINED,  # noqa: A002
        metavar: str = UNDEFINED,
        nargs: str | int | None = UNDEFINED,
        required: bool = UNDEFINED,
        type: Callable[[Any], Any] = UNDEFINED,  # noqa: A002
    ) -> Self:
        """Factory method."""
        return cls(
            flags=flags or UNDEFINED,
            action=action,
            choices=choices,
            const=const,
            default=default,
            dest=dest,
            help=help,
            metavar=metavar,
            nargs=nargs,
            required=required,
            type=type,
        )


option = Option.factory


def add_option(
    *flags: str,
    default: Any = None,
    action: str | None = UNDEFINED,
    choices: Container[Any] = UNDEFINED,
    const: Any = UNDEFINED,
    dest: str = UNDEFINED,
    help: str = UNDEFINED,  # noqa: A002
    metavar: str = UNDEFINED,
    nargs: str | int | None = UNDEFINED,
    required: bool = UNDEFINED,
    type: Callable[[Any], Any] = UNDEFINED,  # noqa: A002
    **field_kws: Any,  # noqa: ARG001
) -> Any:
    """Add option."""
    return field(  # pylint: disable=invalid-field-call
        metadata={
            "option": Option.factory(
                *flags,
                default=default,
                action=action,
                choices=choices,
                const=const,
                dest=dest,
                help=help,
                metavar=metavar,
                nargs=nargs,
                required=required,
                type=type,
            ),
        },
        default=default,
    )


class DataclassParser:
    """Mixin for creating a dataclass with parsing."""

    @classmethod
    def parser(cls, prefix_char: str = "-", **kwargs: Any) -> ArgumentParser:
        """Get parser."""
        parser = ArgumentParser(prefix_chars=prefix_char, **kwargs)

        for opt in get_dataclass_options(cls).values():
            opt.add_argument_to_parser(parser, prefix_char=prefix_char)

        return parser

    @classmethod
    def from_posargs(
        cls,
        posargs: str | Sequence[str],
        prefix_char: str = "-",
        parser: ArgumentParser | None = None,
        known: bool = False,
    ) -> Self:
        """Create object from posargs."""
        if parser is None:
            parser = cls.parser(prefix_char=prefix_char)

        if isinstance(posargs, str):
            import shlex

            posargs = shlex.split(posargs)

        if known:
            parsed, _ = parser.parse_known_args(posargs)
        else:
            parsed = parser.parse_args(posargs)

        return cls(**vars(parsed))


def get_dataclass_options(cls: Any) -> dict[str, Option]:
    """Get dictionary of options."""
    return {
        name: _create_option(name=name, opt=opt, annotation=annotation)
        for name, (annotation, opt) in _get_dataclass_annotations_and_options(
            cls,
        ).items()
    }


def _get_dataclass_annotations_and_options(
    cls: Any,
) -> dict[str, tuple[Any, Option]]:
    annotations = get_type_hints(cls, include_extras=True)

    assert is_dataclass(cls)  # noqa: S101
    cls_fields = fields(cls)

    out: dict[str, tuple[Any, Any]] = {}
    for f in cls_fields:
        if f.name.startswith("_") or not f.init:
            continue

        opt = f.metadata.get("option", Option(default=f.default))

        # Can also pass via annotations
        annotation = annotations[f.name]
        if get_origin(annotation) is Annotated:
            annotation, opt_anno, *_ = get_args(annotation)
            if isinstance(opt_anno, Option):
                opt = Option(**{**opt_anno.asdict(), **opt.asdict()})

        out[f.name] = (annotation, opt)
    return out


def _create_option(
    name: str,
    opt: Option,
    annotation: Any,
) -> Option:
    depth, underlying_type = _get_underlying_type(annotation)
    max_depth = 2

    if depth <= max_depth and get_origin(underlying_type) is Literal:
        choices = get_args(underlying_type)
        if opt.choices is UNDEFINED:
            opt = replace(opt, choices=choices)
    else:
        choices = None

    if opt.nargs is UNDEFINED and depth > 0:
        opt = replace(opt, nargs="*")

    if opt.action is UNDEFINED and depth > 1:
        opt = replace(opt, action="append")

    if opt.type is UNDEFINED:
        opt_type = type(choices[0]) if choices else underlying_type  # pyright: ignore[reportUnknownVariableType]

        if not callable(opt_type):  # pyright: ignore[reportUnknownArgumentType]
            msg = (
                f"Annotation {annotation} for parameter {name!r} is not callable."
                f"Declare arg type with Annotated[..., Option(type=...)] instead."
            )
            raise TypeError(
                msg,
            )
        opt = replace(opt, type=opt_type)

    if opt.type is bool:
        opt = replace(
            opt,
            action="store_false" if opt.default is True else "store_true",
            type=UNDEFINED,
            default=UNDEFINED,
        )

    if opt.flags is UNDEFINED or not opt.flags:
        opt = replace(opt, flags="--" + name.replace("_", "-"))

    return opt


def _get_underlying_type(
    opt: Any,
    allow_optional: bool = True,
    depth: int = 0,
    max_depth: int = 2,
) -> tuple[int, Any]:
    """
    Parse nested list of type -> (depth, type)

    list[list[str]] -> (2, str)
    """
    depth_out = depth

    type_: Any = opt

    if depth > max_depth or ((opt_origin := get_origin(opt)) is None):
        pass

    elif opt_origin is list:
        opt_arg, *extras = get_args(opt)
        if not extras:
            depth_out, type_ = _get_underlying_type(
                opt_arg,
                allow_optional=False,
                depth=depth + 1,
                max_depth=max_depth,
            )

    elif allow_optional and (underlying := _get_underlying_if_optional(opt)):  # pylint: disable=confusing-consecutive-elif
        depth_out, type_ = _get_underlying_type(
            underlying,
            allow_optional=False,
            depth=depth,
            max_depth=max_depth,
        )

    return depth_out, type_


def _get_underlying_if_optional(t: Any, pass_through: bool = False) -> Any:
    if _is_union_type(t):
        args = get_args(t)
        if len(args) == 2 and _NoneType in args:  # noqa: PLR2004
            for arg in args:
                if arg != _NoneType:
                    return arg
    elif pass_through:  # pylint: disable=confusing-consecutive-elif
        return t

    return None


def _is_union_type(t: Any) -> bool:
    # types.UnionType only exists in Python 3.10+.
    # https://docs.python.org/3/library/stdtypes.html#types-union
    import types

    origin = get_origin(t)
    return origin is types.UnionType or origin is Union  # pylint: disable=consider-alternative-union-syntax)   # pyright: ignore[reportDeprecated]
