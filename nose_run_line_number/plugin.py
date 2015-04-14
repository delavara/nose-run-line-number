__test__ = False

import logging
import os
import ast
from nose.plugins import Plugin

log = logging.getLogger('nose.plugins.runlinenumber')


class MethodFinder(ast.NodeVisitor):
    def __init__(self, line_to_match, test_pattern, level):
        self.matched_function = None
        self.matched_class = None
        self.level = level
        self.line_to_match = line_to_match
        self.test_pattern = test_pattern
        self.function_lines = {}
        self.class_lines = {}

    def visit_ClassDef(self, node):
        self.current_class = node.name

        last_line_of_class = node.body[-1].lineno
        for line_no in range(node.lineno, last_line_of_class + 1):
            self.class_lines[line_no] = self.current_class

        super(MethodFinder, self).generic_visit(node)

    def visit_FunctionDef(self, node):
        if self.test_pattern.match(node.name):
            self.current_function = node.name

        last_line_of_fun = node.body[0].lineno
        for line_no in range(node.lineno, last_line_of_fun + 1):
            self.function_lines[line_no] = self.current_function

        super(MethodFinder, self).generic_visit(node)

class RunLineNumber(Plugin):
    name = 'runlinenumber'

    def options(self, parser, env=os.environ):
        parser.add_option(
                '--line', dest='linenum', metavar='LINE', type='int',
                help="Run test specified on this line")
        parser.add_option(
                '--line-file', dest='linefile', metavar='File',
                help="file to run the test on (used for setuptools integration)")
        parser.add_option(
                '--level', dest='level', metavar='LEVEL', type='str', default='method',
                help="Level to run for this line (method, class, file)")

    def configure(self, options, conf):
        if options.linenum:
            self.enabled = True

            if options.linefile:
                test_name = options.linefile
            else:
                if len(conf.testNames) < 1:
                    log.error("must specify a test file to run")
                    self.matched_function = None
                    return

                test_name = self.findTestName(conf.testNames)

            with open(test_name, 'r') as f:
                ast_node = ast.parse(f.read())
            linenum = options.linenum
            self.level = options.level
            self.testMatch = conf.testMatch
            finder = MethodFinder(linenum, conf.testMatch, options.level)
            finder.visit(ast_node)

            self.matched_function = finder.function_lines.get(linenum)
            self.matched_class = finder.class_lines.get(linenum)
            while linenum > 0:
                linenum -= 1
                if self.matched_function is None:
                    self.matched_function = finder.function_lines.get(linenum)
                if self.matched_class is None:
                    self.matched_class = finder.class_lines.get(linenum)

            log.info("Matched function: %s with line %d" % (self.matched_function, options.linenum))

    def findTestName(self, testNames):
        if testNames[0] == '.' and len(testNames) > 1:
            return testNames[1]
        else:
            return testNames[0]

    def wantMethod(self, method):
        func_name = method.im_func.func_name
        if self.testMatch.match(func_name) and method.im_class.__name__ == self.matched_class:
            if self.level == 'method':
                return func_name == self.matched_function
            return True
        else:
            return False
