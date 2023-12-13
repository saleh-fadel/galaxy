"""This module contains a linting functions for tool tests."""
from typing import (
    List,
    Optional,
    TYPE_CHECKING,
)

from galaxy.tool_util.lint import Linter
from galaxy.util import asbool
from ._util import is_datasource

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource
    from galaxy.util.etree import Element

lint_tool_types = ["default", "data_source", "manage_data"]


class TestsMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        root = tool_xml.find("./tests")
        if root is None:
            root = tool_xml.getroot()
        if len(tests) == 0 and not is_datasource(tool_xml):
            lint_ctx.warn("No tests found, most tools should define test cases.", node=root)


class TestsMissingDatasource(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        root = tool_xml.find("./tests")
        if root is None:
            root = tool_xml.getroot()
        if len(tests) == 0 and is_datasource(tool_xml):
            lint_ctx.info("No tests found, that should be OK for data_sources.", node=root)


class TestsAssertsMultiple(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # TODO same would be nice also for assert_contents
            for ta in ("assert_stdout", "assert_stderr", "assert_command"):
                if len(test.findall(ta)) > 1:
                    lint_ctx.error(
                        f"Test {test_idx}: More than one {ta} found. Only the first is considered.", node=test
                    )


class TestsAssertsHasNQuant(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for a in test.xpath(
                ".//*[self::assert_contents or self::assert_stdout or self::assert_stderr or self::assert_command]//*"
            ):
                if a.tag not in ["has_n_lines", "has_n_columns"]:
                    continue
                if not (set(a.attrib) & set(["n", "min", "max"])):
                    lint_ctx.error(f"Test {test_idx}: '{a.tag}' needs to specify 'n', 'min', or 'max'", node=a)


class TestsAssertsHasSizeQuant(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for a in test.xpath(
                ".//*[self::assert_contents or self::assert_stdout or self::assert_stderr or self::assert_command]//*"
            ):
                if a.tag != "has_size":
                    continue
                if len(set(a.attrib) & set(["value", "min", "max"])) == 0:
                    lint_ctx.error(f"Test {test_idx}: '{a.tag}' needs to specify 'value', 'min', or 'max'", node=a)


class TestsExpectNumOutputs(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # check if expect_num_outputs is set if there are outputs with filters
            # (except for tests with expect_failure .. which can't have test outputs)
            filter = tool_xml.find("./outputs//filter")
            if not (
                filter is None
                or "expect_num_outputs" in test.attrib
                or asbool(test.attrib.get("expect_failure", False))
            ):
                lint_ctx.warn(
                    f"Test {test_idx}: should specify 'expect_num_outputs' if outputs have filters", node=test
                )


class TestsParamInInputs(Linter):
    """
    really simple linter that test parameters are also present in the inputs
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for param in test.findall("param"):
                name = param.attrib.get("name", None)
                if not name:
                    continue
                name = name.split("|")[-1]
                xpaths = [f"@name='{name}'", f"@argument='{name}'", f"@argument='-{name}'", f"@argument='--{name}'"]
                if "_" in name:
                    xpaths += [f"@argument='-{name.replace('_', '-')}'", f"@argument='--{name.replace('_', '-')}'"]
                found = False
                for xp in xpaths:
                    inxpath = f".//inputs//param[{xp}]"
                    inparam = tool_xml.findall(inxpath)
                    if len(inparam) > 0:
                        found = True
                        break
                if not found:
                    lint_ctx.error(f"Test {test_idx}: Test param {name} not found in the inputs", node=param)


class TestsOutputName(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # note output_collections are covered by xsd, but output is not required to have one by xsd
            for output in test.findall("output"):
                if not output.attrib.get("name", None):
                    lint_ctx.error(f"Test {test_idx}: Found {output.tag} tag without a name defined.", node=output)


class TestsOutputDefined(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    lint_ctx.error(
                        f"Test {test_idx}: Found {output.tag} tag with unknown name [{name}], valid names {list(output_data_or_collection)}",
                        node=output,
                    )


class TestsOutputCorresponding(Linter):
    """
    Linter checking if test/output corresponds to outputs/data
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if output.tag == "output" and corresponding_output.tag != "data":
                    lint_ctx.error(
                        f"Test {test_idx}: test output {name} does not correspond to a 'data' output, but a '{corresponding_output.tag}'",
                        node=output,
                    )


class TestsOutputCollectionCorresponding(Linter):
    """
    Linter checking if test/collection corresponds to outputs/output_collection
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if output.tag == "output_collection" and corresponding_output.tag != "collection":
                    lint_ctx.error(
                        f"Test {test_idx}: test collection output '{name}' does not correspond to a 'output_collection' output, but a '{corresponding_output.tag}'",
                        node=output,
                    )


class TestsOutputCompareAttrib(Linter):
    """
    Linter checking compatibility of output attributes with the value
    of the compare attribute
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        COMPARE_COMPATIBILITY = {
            "sort": ["diff", "re_match", "re_match_multiline"],
            "lines_diff": ["diff", "re_match", "contains"],
            "decompress": ["diff"],
            "delta": ["sim_size"],
            "delta_frac": ["sim_size"],
        }
        for test_idx, test in enumerate(tests, start=1):
            for output in test.xpath(".//*[self::output or self::element or self::discovered_dataset]"):
                compare = output.get("compare", "diff")
                for attrib in COMPARE_COMPATIBILITY:
                    if attrib in output.attrib and compare not in COMPARE_COMPATIBILITY[attrib]:
                        lint_ctx.error(
                            f'Test {test_idx}: Attribute {attrib} is incompatible with compare="{compare}".',
                            node=output,
                        )


class TestsOutputCheckDiscovered(Linter):
    """
    Linter checking that discovered elements of outputs are tested with
    a count attribute or listing some discovered_dataset
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                discover_datasets = corresponding_output.find(".//discover_datasets")
                if discover_datasets is None:
                    continue
                if "count" not in output.attrib and output.find("./discovered_dataset") is None:
                    lint_ctx.error(
                        f"Test {test_idx}: test output '{name}' must have a 'count' attribute and/or 'discovered_dataset' children",
                        node=output,
                    )


class TestsOutputCollectionCheckDiscovered(Linter):
    """
    Linter checking that discovered elements of output collections
    are tested with a count attribute or listing some elements
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue
                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                discover_datasets = corresponding_output.find(".//discover_datasets")
                if discover_datasets is None:
                    continue
                if "count" not in output.attrib and output.find("./element") is None:
                    lint_ctx.error(
                        f"Test {test_idx}: test collection '{name}' must have a 'count' attribute or 'element' children",
                        node=output,
                    )


class TestsOutputCollectionCheckDiscoveredNested(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if corresponding_output.find(".//discover_datasets") is None:
                    continue
                if corresponding_output.get("type", "") in ["list:list", "list:paired"]:
                    nested_elements = output.find("./element/element")
                    element_with_count = output.find("./element[@count]")
                    if nested_elements is None and element_with_count is None:
                        lint_ctx.error(
                            f"Test {test_idx}: test collection '{name}' must contain nested 'element' tags and/or element children with a 'count' attribute",
                            node=output,
                        )


class TestsOutputFailing(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            if not asbool(test.attrib.get("expect_failure", False)):
                continue
            if test.find("output") is not None or test.find("output_collection") is not None:
                lint_ctx.error(f"Test {test_idx}: Cannot specify outputs in a test expecting failure.", node=test)


class TestsExpectNumOutputsFailing(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            if not asbool(test.attrib.get("expect_failure", False)):
                continue
            if test.find("output") is not None or test.find("output_collection") is not None:
                continue
            if "expect_num_outputs" in test.attrib:
                lint_ctx.error(
                    f"Test {test_idx}: Cannot make assumptions on the number of outputs in a test expecting failure.",
                    node=test,
                )


class TestsHasExpectations(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        _check_and_count_valid(tests, lint_ctx)


class TestsNoValid(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        general_node = tool_xml.find("./tests")
        if general_node is None:
            general_node = tool_xml.getroot()
        tests = tool_xml.findall("./tests/test")
        if not tests:
            return
        num_valid_tests = _check_and_count_valid(tests, None)
        if num_valid_tests or is_datasource(tool_xml):
            lint_ctx.valid(f"{num_valid_tests} test(s) found.", node=general_node)


class TestsValid(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        general_node = tool_xml.find("./tests")
        if general_node is None:
            general_node = tool_xml.getroot()
        tests = tool_xml.findall("./tests/test")
        if not tests:
            return
        num_valid_tests = _check_and_count_valid(tests, None)
        if not (num_valid_tests or is_datasource(tool_xml)):
            lint_ctx.warn("No valid test(s) found.", node=general_node)


def _check_and_count_valid(tests: List["Element"], lint_ctx: Optional["LintContext"] = None):
    num_valid = 0
    for test_idx, test in enumerate(tests, start=1):
        valid = False
        valid |= bool(set(test.attrib) & set(("expect_failure", "expect_exit_code", "expect_num_outputs")))
        for ta in ("assert_stdout", "assert_stderr", "assert_command"):
            if test.find(ta) is not None:
                valid = True
        found_output_test = test.find("output") is not None or test.find("output_collection") is not None
        if asbool(test.attrib.get("expect_failure", False)):
            if found_output_test or "expect_num_outputs" in test.attrib:
                continue
        valid |= found_output_test
        if not valid:
            if lint_ctx:
                lint_ctx.warn(
                    f"Test {test_idx}: No outputs or expectations defined for tests, this test is likely invalid.",
                    node=test,
                )
        else:
            num_valid += 1
    return num_valid


def _collect_output_names(tool_xml):
    """
    determine dict mapping the names of data and collection outputs to the
    corresponding nodes
    """
    output_data_or_collection = {}
    outputs = tool_xml.findall("./outputs")
    if len(outputs) == 1:
        for output in list(outputs[0]):
            name = output.attrib.get("name", None)
            if not name:
                continue
            output_data_or_collection[name] = output
    return output_data_or_collection
