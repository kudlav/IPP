# coding=utf-8

import getopt
import sys
import xml.etree.ElementTree as etree
import re


class Enviroment:
    """The class represents enviroment of process. Contains stacks and frame (variables storage)"""
    def __init__(self):
        self.gf = {}
        self.lf = None
        self.tf = None
        self.stack = []
        self.label = {}  # {string: int}
        self.call = []  # int[]


class Variable:
    """The class used for storing any value. Contains value and it's type"""
    def __init__(self, datatype=None, value=None):
        self.type = datatype
        self.value = value

    def __repr__(self):
        return str(self.type)+"@"+str(self.value)


class Argument:
    """The class represents argX element. Contains value and it's type (eg. int, var, type...)"""
    def __init__(self, argtype, value):
        self.type = argtype
        self.value = value


def help_print():
    """
    Print description, usage and return codes of this script.
    # type: () -> None
    """
    print("Nacte a interpretuje XML reprezentaci programu ze souboru.\n"
          "\n"
          "Pouziti:\n"
          "./interpret.py --source=<file> [--help]\n"
          "  --source=<file>\n"
          "    vstupni soubor s XML reprezentaci zdrojoveho kodu\n"
          "  --help\n"
          "    vypise na standardni vystup napovedu\n"
          "\n"
          "Navratove kody:\n"
          "  0    ok\n"
          "  10   chyba pri zpracovani argumentu"
          "  11   chyba nacitani vstupniho souboru"
          "  31   XML format vstupniho souboru nema pozadovany format"
          "  32   lexikalni nebo syntakticka chyba"
          "  53   behova chyba interpretace – spatne typy operandu"
          "  54   behova chyba interpretace – pristup k neexistujici promenne (ramec existuje)"
          "  55   behova chyba interpretace – ramec neexistuje (napr. cteni z prazdneho zasobníku ramcu)"
          "  56   behová chyba interpretace – chybejici hodnota (v promenne nebo na zasobniku)"
          "  57   behová chyba interpretace – deleni nulou"
          "  58   behová chyba interpretace – chybna prace s retezcem"
          "  59   behová chyba interpretace – pokus o redefinovani promenne"
          )


def error(order, errno, msg):
    """
    Print error message to stderr with number of line and exit program with specified return code.
    # type: (int, int, str) -> None
    """
    sys.stderr.write(msg + ", instrukce " + str(order) + "\n")
    sys.exit(errno)


def load_xml(filepath):
    """
    Get root "program" element from specified file, exit program if error occurs.
    # type: (str) -> etree.Element
    """
    try:
        tree = etree.parse(filepath)
    except FileNotFoundError:
        sys.stderr.write('Soubor "' + filepath + '" neexistuje\n')
        sys.exit(11)
    except etree.ParseError as err:
        sys.stderr.write('Soubor "' + filepath + '" neobsahuje platny XML soubor\n' + err.msg + "\n")
        sys.exit(31)

    root = tree.getroot()
    if root.tag != "program" or root.get("language") != "IPPcode18":
        sys.stderr.write('Chybi korenovy element "program" s atributem "language=IPPcode18"\n')
        sys.exit(31)
    return root


def parse_args(child, order, argc):
    """
    Get array of Argument from instruction xml element.
    Also check number of arguments and exit program when element is not valid.
    # type: (etree.Element, int, int) -> list
    """
    if len(child) != argc:
        sys.stderr.write('Instrukce ' + str(order) + ' ocekava ' + str(argc) + ' argument(y), predano: ' + str(len(child)) + "\n")
        sys.exit(32)

    arg = []
    for i in range(1, argc+1):
        arg_tag = child.find("arg" + str(i))
        if arg_tag is None:
            error(order, 31, 'Instrukce neobsahuje tag "arg' + str(i) + '"')
        if arg_tag.get("type") is None:
            error(order, 32, 'Argumentu ' + child[i-1].tag + ' chybi atribut "type"')
        arg.append(Argument(arg_tag.get("type"), arg_tag.text))

    return arg


def parse_type(order, arg):
    """
    Check whether Argument is valid type name.

    Return name of type if valid, otherwise exit program.
    # type: (int, Argument) -> str
    """
    if arg.type != "type":
        error(order, 53, 'Ocekavan argument typu "type", uveden: "' + arg.type + '"')
    if arg.value not in ["int", "string", "bool", "float"]:
        error(order, 53, 'Argument "' + arg.value + '" typu "type" nesplnuje pozadovany tvar')
    return arg.value


def parse_label(order, arg):
    """
    Check whether Argument is valid label name.

    Return name of label if valid, otherwise exit program.
    # type: (int, Argument) -> str
    """
    if arg.type != "label":
        error(order, 53, 'Ocekavan argument typu "label", uveden: "' + arg.type + '"')
    if arg.value is None or re.fullmatch("[a-zA-Z_\-$&%*][\w_\-$&%*]*", arg.value) is None:
        error(order, 53, 'Argument "' + str(arg.value) + '" typu "label" nesplnuje pozadovany tvar')
    return arg.value


def parse_var(order, arg):
    """
    Check whether Argument is valid variable identificator.

    Return variable identificator splitted into parts if valid, otherwise exit program.
    [0]=origin string, [1]=scope (LF/TF/GF), [2]=variable name
    # type: (int, Argument) -> list
    """
    if arg.type != "var":
        error(order, 53, 'Ocekavan argument typu "var", uveden: "' + arg.type + '"')
    if arg.value is not None:
        match = re.fullmatch("(LF|TF|GF)@([a-zA-Z_\-$&%*][\w_\-$&%*]*)", arg.value)
    if arg.value is None or match is None:
        error(order, 53, 'Argument "' + str(arg.value) + '" typu "var" nesplnuje pozadovany tvar')
    return match


def get_var(enviroment, order, match, write=False):
    """
    Get link to existing Variable from parsed variable identification gain from parse_var function.

    If trying to write into undefined variable or define already defined variable, exit program.
    # type: (Enviroment, int, list, bool) -> Variable
    """
    var = None
    if match[1] == "GF":
        var = enviroment.gf.get(match[2])
    elif match[1] == "TF":
        if enviroment.tf is None:
            error(order, 55, "Docasny ramec neni definovan")  # exit(55)
        var = enviroment.tf.get(match[2])
    elif match[1] == "LF":
        if enviroment.lf is None:
            error(order, 55, "Lokalni ramec neni nedefinovan")  # exit(55)
        var = enviroment.lf[-1].get(match[2])
    if var is not None and write:
        error(ip, 59, 'Pokus o redefinovani promenne "' + match[0])  # exit(59)
    if var is None and not write:
        error(ip, 54, 'Pristup k neexistujici promenne "' + match[0] + '"')  # exit(54)
    return var


def get_symb(enviroment, order, arg, undefined=False):
    """
    Parse and Get new virtual Variable object from Argument.

    # type: (Enviroment, int, Argument, bool) -> Variable
    """
    var = Variable(arg.type)
    if arg.type == "int":
        try:
            var.value = int(arg.value)
        except (ValueError, TypeError):
            error(order, 53, 'Hodnota "' + str(arg.value) + '" neni typu int')  # exit(55)
    elif arg.type == "bool":
        if arg.value == "true":
            var.value = True
        elif arg.value == "false":
            var.value = False
        else:
            error(order, 53, 'Hodnota "' + str(arg.value) + '" neni typu bool')  # exit(55)
    elif arg.type == "string":
        if arg.value is None:
            var.value = ""
        else:
            if re.fullmatch("([^\s#\\\\]|\\\\\d{3})+", arg.value) is None:
                error(order, 53, 'Argument "' + arg.value + '" typu "string" nesplnuje pozadovany tvar')
            occurences = re.findall("\\\\\d{3}", arg.value)
            for repl in occurences:
                try:
                    arg.value = arg.value.replace(repl, chr(int(repl[1:])), 1)
                except ValueError:
                    error(ip, 58, "Escape hodnota v retezci neodpovida kodu Unicode")  # exit(58)
            var.value = arg.value
    elif arg.type == "float":
        try:
            var.value = float.fromhex(arg.value)
        except (ValueError, TypeError):
            error(order, 53, 'Hodnota "' + str(arg.value) + '" neni typu float')  # exit(55)
    elif arg.type == "var":
        match = parse_var(order, arg)
        var = get_var(enviroment, order, match)
        if var.type is None or var.value is None:
            if undefined:
                return None
            error(order, 56, 'Promenne "' + arg.value + '" nebyla dosud prirazena hodnota')  # exit(56)
    else:
        error(order, 53, 'Ocekavan argument typu int/bool/string/float nebo var, uveden: "' + arg.type + '"')
    return var


def write_stats(statpath, stati, i_count, v_count):
    """
    Write statistics if statpath is set according to STATI arguments.
    # type: (str, list, int, int) -> None
    """
    if statpath != "":
        try:
            with open(statpath, 'w') as file:
                for st in stati:
                    if st == "insts":
                        file.write(str(i_count) + "\n")
                    else:
                        file.write(str(v_count) + "\n")
        except (PermissionError, FileNotFoundError):
            sys.stderr.write('Chyba pri otevirani souboru "' + statpath + ' pro zapis statistik"\n')
            sys.exit(11)


if __name__ == "__main__":
    # Parse CLI arguments
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hs:", ["help", "source=", "stats=", "insts", "vars"])
    except getopt.GetoptError as err:
        if err.opt != "":
            sys.stderr.write("Nespravne pouziti parametru: " + err.opt + "\n")
            help_print()
        sys.exit(10)

    filepath = ""
    statpath = ""
    stati = []

    for option, value in opts:
        if option in ("-h", "--help"):
            help_print()
            sys.exit(0)
        elif option in ("-s", "--source"):
            filepath = value
        elif option == "--stats":
            statpath = value
        elif option == "--insts":
            if len(stati) != 0 and stati[0] == "insts":
                sys.stderr.write("Argument 'insts' byl pouzit dvakrat.\n")
                help_print()
                sys.exit(10)
            stati.append("insts")
        elif option == "--vars":
            if len(stati) != 0 and stati[0] == "vars":
                sys.stderr.write("Argument 'vars' byl pouzit dvakrat.\n")
                help_print()
                sys.exit(10)
            stati.append("vars")
        else:
            sys.stderr.write("Neznamy parametr: " + option + "\n")
            help_print()
            sys.exit(10)

    if len(stati) > 0 and statpath == "":
        sys.stderr.write("Parametry --insts ci --vars musi byt pouzity spolu se --stats\n")
        help_print()
        sys.exit(10)

    if filepath == "":
        sys.stderr.write("Chyby povinny parametr: --source=<file>\n")
        help_print()
        sys.exit(10)

    # Load and parse XML
    root = load_xml(filepath)

    # Check for syntax errors and find index of all LABELs, order instructions
    enviroment = Enviroment()
    instructions = {}
    i_count = 0
    ip = 1
    while ip < len(root)+1:
        child = root[ip-1]

        if child.tag != "instruction":
            sys.stderr.write('Ocekavan element "instruction", nalezen "' + child.tag + '"\n')
            sys.exit(31)

        if child.get("order") is None:
            sys.stderr.write(str(ip) + '. element "instruction" neobsahuje atribut order\n')
            sys.exit(31)

        try:
            order = int(child.get("order"))
            if order <= 0:
                raise ValueError
        except ValueError:
            sys.stderr.write('Atribut order musi obsahovat cele cislo, predano: "' + child.get("order") + '"\n')
            sys.exit(31)
        if order in instructions:
            sys.stderr.write("Program obsahuje dve instrukce s poradim " + str(order) + "\n")
            sys.exit(31)
        instructions[order] = child

        if child.get("opcode").upper() == "LABEL":
            args = parse_args(child, ip, 1)  # exit(32)
            label = parse_label(ip, args[0])
            if label in enviroment.label:
                error(ip, 56, 'Pokus o redefinovani navesti "' + label + '"')  # exit(56)
            enviroment.label[label] = ip
        ip += 1

    # Check continuity of order number
    for i in range(1, len(root)+1):
        if i not in instructions:
            sys.stderr.write("Chybi instrukce s poradovym cislem " + str(i) + "\n")
            sys.exit(31)

    # Browse instruction elements
    i_count = 0
    v_count = 0
    ip = 1
    while ip < len(root)+1:
        child = instructions.get(ip)

        opcode = child.get("opcode").upper()

        # PARSING INSTRUCTION #
        if opcode == "CREATEFRAME":
            parse_args(child, ip, 0)  # exit(32)
            enviroment.tf = {}

        elif opcode == "PUSHFRAME":
            parse_args(child, ip, 0)  # exit(32)
            if enviroment.tf is None:
                error(ip, 55, "Docasny ramec nedefinovan, neni co vlozit na zasobnik ramcu")  # exit(55)
            if enviroment.lf is None:
                enviroment.lf = []
            enviroment.lf.append(enviroment.tf)
            enviroment.tf = None

        elif opcode == "POPFRAME":
            parse_args(child, ip, 0)  # exit(32)
            if enviroment.lf is None:
                error(ip, 55, "Seznam lokalnich ramcu je prazdny, neni co vybrat")  # exit(55)
            enviroment.tf = enviroment.lf.pop()
            if len(enviroment.lf) == 0:
                enviroment.lf = None

        elif opcode == "RETURN":
            parse_args(child, ip, 0)  # exit(32)
            if len(enviroment.call) == 0:
                error(ip, 56, "Cteni z prazdneho zasobniku volani")  # exit(56)
            ip = enviroment.call.pop()

        elif opcode == "BREAK":
            parse_args(child, ip, 0)  # exit(32)
            sys.stderr.write("Instrukce: " + str(ip) + "\n"
                             "Vykonano instrukci: " + str(i_count) + "\n"
                             "Zasobnik volani: " + str(enviroment.call) + "\n"
                             "Zasobnik navesti: " + str(enviroment.label) + "\n"
                             "Datovy zasobnik: " + str(enviroment.stack) + "\n"
                             "Globalni ramec: " + str(enviroment.gf) + "\n"
                             "Lokalni ramce: " + str(enviroment.lf) + "\n"
                             "Docasny ramec: " + str(enviroment.tf) + "\n"
                             )

        elif opcode == "CALL":
            args = parse_args(child, ip, 1)  # exit(32)
            label = parse_label(ip, args[0])
            if label not in enviroment.label:
                error(ip, 52, 'Navesti "' + label + '" nenalezeno')  # exit(52)
            enviroment.call.append(ip)
            ip = enviroment.label.get(label)

        elif opcode == "JUMP":
            args = parse_args(child, ip, 1)  # exit(32)
            label = parse_label(ip, args[0])
            if label not in enviroment.label:
                error(ip, 52, 'Navesti "' + label + '" nenalezeno')  # exit(52)
            ip = enviroment.label.get(label)

        elif opcode == "DEFVAR":
            args = parse_args(child, ip, 1)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match, True)
            if match[1] == "GF":
                enviroment.gf[match[2]] = Variable()
            elif match[1] == "TF":
                enviroment.tf[match[2]] = Variable()
            elif match[1] == "LF":
                enviroment.lf[-1][match[2]] = Variable()
            # Compute variables for STATI:
            actual_count = len(enviroment.gf)
            if enviroment.tf is not None:
                actual_count += len(enviroment.tf)
            if enviroment.lf is not None:
                for lf in enviroment.lf:
                    actual_count += len(lf)
            if actual_count > v_count:
                v_count = actual_count

        elif opcode == "POPS":
            args = parse_args(child, ip, 1)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            if len(enviroment.stack) == 0:
                error(ip, 56, 'Datovy zasovnik je prazdny "' + match[2])  # exit(56)
            src = enviroment.stack.pop()
            var.type = src.type
            var.value = src.value

        elif opcode == "PUSHS":
            args = parse_args(child, ip, 1)  # exit(32)
            symb = get_symb(enviroment, ip, args[0])  # exit(55/54)
            enviroment.stack.append(symb)

        elif opcode == "WRITE":
            args = parse_args(child, ip, 1)  # exit(32)
            symb = get_symb(enviroment, ip, args[0])  # exit(55/54)
            if symb.type == "bool":
                print(str(symb.value).lower())
            else:
                print(symb.value)

        elif opcode == "DPRINT":
            args = parse_args(child, ip, 1)  # exit(32)
            symb = get_symb(enviroment, ip, args[0])  # exit(55/54)
            if symb.type == "bool":
                sys.stderr.write(str(symb.value).lower() + "\n")
            else:
                sys.stderr.write(symb.value + "\n")

        elif opcode == "MOVE":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            var.type = symb.type
            var.value = symb.value

        elif opcode == "TYPE":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1], True)  # exit(54/55/56)
            var.type = "string"
            if symb is not None:
                var.value = symb.type
            else:
                var.value = ""

        elif opcode == "STRLEN":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1], True)  # exit(54/55/56)
            if symb.type != "string":
                error(ip, 53, "arg2 instrukce STRLEN musi byt retezec")
            var.type = "int"
            var.value = len(symb.value)

        elif opcode == "INT2CHAR":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            try:
                if symb.type != "int":
                    raise ValueError
                var.value = chr(symb.value)
            except ValueError:
                error(ip, 58, "arg2 instrukce INT2CHAR musi byt hodnota Unicode")  # exit(58)
            var.type = "string"

        elif opcode in ["ADD", "SUB", "MUL", "IDIV"]:
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != symb2.type or (symb1.type != "int" and symb1.type != "float"):
                error(ip, 53, opcode + ': arg2 a arg3 musi byt typu int a int nebo typu float a float')  # exit(53)
            var.type = symb1.type
            if opcode == "ADD":
                var.value = symb1.value + symb2.value
            elif opcode == "SUB":
                var.value = symb1.value - symb2.value
            elif opcode == "MUL":
                var.value = symb1.value * symb2.value
            elif opcode == "IDIV":
                if symb2.value == 0:
                    error(ip, 57, "IDIV: Deleni nulou")  # exit(57)
                var.value = symb1.value // symb2.value

        elif opcode == "CONCAT":
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != "string" or symb2.type != "string":
                error(ip, 53, 'CONCAT: arg2 a arg3 instrukce musi byt retezec')  # exit(53)
            var.type = "string"
            var.value = symb1.value + symb2.value

        elif opcode == "STRI2INT":
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != "string" or symb2.type != "int":
                error(ip, 53, 'STRI2INT: arg2 musi byt retezec a arg3 cele cislo')  # exit(53)
            if symb2.value < 0 or symb2.value >= len(symb1.value):
                error(ip, 58, 'STRI2INT: pristup mimo rozsah retezce')  # exit(58)
            var.type = "int"
            var.value = ord(symb1.value[symb2.value])

        elif opcode == "GETCHAR":
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != "string" or symb2.type != "int":
                error(ip, 53, 'GETCHAR: arg2 musi byt retezec a arg3 cele cislo')  # exit(53)
            if symb2.value < 0 or symb2.value >= len(symb1.value):
                error(ip, 58, 'GETCHAR: pristup mimo rozsah retezce')  # exit(58)
            var.type = "string"
            var.value = symb1.value[symb2.value]

        elif opcode == "SETCHAR":
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != "int" or symb2.type != "string":
                error(ip, 53, 'SETCHAR: arg2 musi byt retezec a arg3 cele cislo')  # exit(53)
            if symb1.value < 0 or symb1.value >= len(var.value):
                error(ip, 58, 'SETCHAR: pristup mimo rozsah retezce')  # exit(58)
            if len(symb2.value) <= 0:
                error(ip, 58, 'SETCHAR: symb2 musi byt neprazdny rezetec')  # exit(58)
            var.value = var.value[:symb1.value] + symb2.value[0] + var.value[symb1.value+1:]

        elif opcode in ["JUMPIFEQ", "JUMPIFNEQ"]:
            args = parse_args(child, ip, 3)  # exit(32)
            label = parse_label(ip, args[0])
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if label not in enviroment.label:
                error(ip, 52, 'Navesti "' + label + '" nenalezeno')  # exit(52)
            if symb1.type != symb2.type:
                error(ip, 53, opcode + ': arg2 a arg3 museji byt stejneho typu')  # exit(53)
            if opcode == "JUMPIFEQ" and symb1.value == symb2.value:
                ip = enviroment.label.get(label)
            elif opcode == "JUMPIFNEQ" and symb1.value != symb2.value:
                ip = enviroment.label.get(label)

        elif opcode in ["AND", "OR"]:
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != "bool" or symb2.type != "bool":
                error(ip, 53, opcode + ': arg2 a arg3 musi byt typu bool')  # exit(53)
            var.type = "bool"
            if opcode == "AND":
                var.value = symb1.value and symb2.value
            else:
                var.value = symb1.value or symb2.value

        elif opcode == "NOT":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            if symb.type != "bool":
                error(ip, 53, 'NOT: arg2 musi byt typu bool')  # exit(53)
            var.type = "bool"
            var.value = not symb.value

        elif opcode in ["LT", "GT", "EQ"]:
            args = parse_args(child, ip, 3)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb1 = get_symb(enviroment, ip, args[1])  # exit(54/55/56)
            symb2 = get_symb(enviroment, ip, args[2])  # exit(54/55/56)
            if symb1.type != symb2.type:
                error(ip, 53, opcode + ': arg2 a arg3 museji byt stejneho typu')  # exit(53)
            var.type = "bool"
            if opcode == "LT":
                var.value = symb1.value < symb2.value
            if opcode == "GT":
                var.value = symb1.value > symb2.value
            if opcode == "EQ":
                var.value = symb1.value == symb2.value

        elif opcode == "READ":
            args = parse_args(child, ip, 2)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            typ = parse_type(ip, args[1])
            try:
                inp = input()
            except Exception:
                inp = None
            var.type = typ
            if typ == "int":
                try:
                    var.value = int(inp)
                except (ValueError, TypeError):
                    var.value = 0
            elif typ == "string":
                if inp is not None:
                    var.value = inp
                else:
                    var.value = ""
            elif typ == "bool":
                var.value = inp == "true"
            elif typ == "float":
                try:
                    var.value = float.fromhex(inp)
                except (ValueError, TypeError):
                    error(ip, 53, 'Hodnota "' + str(var.value) + '" neni typu float')  # exit(53)

        elif opcode == "INT2FLOAT":
            args = parse_args(child, ip, 2)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1])
            if symb.type == "int":
                var.type = "float"
                var.value = float(symb.value)
            else:
                error(ip, 53, 'Hodnota "' + str(var.value) + '" neni typu int')  # exit(53)

        elif opcode == "FLOAT2INT":
            args = parse_args(child, ip, 2)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            symb = get_symb(enviroment, ip, args[1])
            if symb.type == "float":
                var.type = "int"
                var.value = int(symb.value)
            else:
                error(ip, 53, 'Hodnota "' + str(var.value) + '" neni typu float')  # exit(53)

        elif opcode == "CLEARS":
            enviroment.stack.clear()

        elif opcode in ["ADDS", "SUBS", "MULS", "IDIVS"]:
            if len(enviroment.stack) < 2:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 2 hodnoty!')  # exit(56)
            symb2 = enviroment.stack.pop()
            symb1 = enviroment.stack.pop()
            if symb1.type != symb2.type or (symb1.type != "int" and symb1.type != "float"):
                error(ip, 53, opcode + ': arg2 a arg3 musi byt typu int a int nebo typu float a float')  # exit(53)
            var = Variable(symb1.type)
            if opcode == "ADDS":
                var.value = symb1.value + symb2.value
            elif opcode == "SUBS":
                var.value = symb1.value - symb2.value
            elif opcode == "MULS":
                var.value = symb1.value * symb2.value
            elif opcode == "IDIVS":
                if symb2.value == 0:
                    error(ip, 57, "IDIV: Deleni nulou")  # exit(57)
                var.value = symb1.value // symb2.value
            enviroment.stack.append(var)

        elif opcode in ["LTS", "GTS", "EQS"]:
            if len(enviroment.stack) < 2:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 2 hodnoty!')  # exit(56)
            symb2 = enviroment.stack.pop()
            symb1 = enviroment.stack.pop()
            if symb1.type != symb2.type:
                error(ip, 53, opcode + ': arg2 a arg3 museji byt stejneho typu')  # exit(53)
            var = Variable(symb1.type)
            if opcode == "LTS":
                var.value = symb1.value < symb2.value
            if opcode == "GTS":
                var.value = symb1.value > symb2.value
            if opcode == "EQS":
                var.value = symb1.value == symb2.value
            enviroment.stack.append(var)

        elif opcode in ["ANDS", "ORS"]:
            if len(enviroment.stack) < 2:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 2 hodnoty!')  # exit(56)
            symb2 = enviroment.stack.pop()
            symb1 = enviroment.stack.pop()
            if symb1.type != "bool" or symb2.type != "bool":
                error(ip, 53, opcode + ': arg2 a arg3 musi byt typu bool')  # exit(53)
            var = Variable("bool")
            if opcode == "ANDS":
                var.value = symb1.value and symb2.value
            else:
                var.value = symb1.value or symb2.value
            enviroment.stack.append(var)

        elif opcode == "NOTS":
            if len(enviroment.stack) < 1:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 1 hodnota!')  # exit(56)
            symb = enviroment.stack.pop()
            if symb.type != "bool":
                error(ip, 53, 'NOT: arg2 musi byt typu bool')  # exit(53)
            var = Variable("bool")
            var.value = not symb.value
            enviroment.stack.append(var)

        elif opcode == "INT2CHARS":
            if len(enviroment.stack) < 1:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 1 hodnota!')  # exit(56)
            symb = enviroment.stack.pop()
            var = Variable("string")
            try:
                if symb.type != "int":
                    raise ValueError
                var.value = chr(symb.value)
            except ValueError:
                error(ip, 58, "Hodnota na datovem zasobniku pro instrukci INT2CHAR musi byt hodnotou Unicode")  # exit(58)
            enviroment.stack.append(var)

        elif opcode == "STRI2INTS":
            if len(enviroment.stack) < 2:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 2 hodnoty!')  # exit(56)
            symb2 = enviroment.stack.pop()
            symb1 = enviroment.stack.pop()
            if symb1.type != "string" or symb2.type != "int":
                error(ip, 53, 'STRI2INT: arg2 musi byt retezec a arg3 cele cislo')  # exit(53)
            if symb2.value < 0 or symb2.value >= len(symb1.value):
                error(ip, 58, 'STRI2INT: pristup mimo rozsah retezce')  # exit(58)
            var = Variable("int")
            var.value = ord(symb1.value[symb2.value])
            enviroment.stack.append(var)

        elif opcode in ["JUMPIFEQS", "JUMPIFNEQS"]:
            args = parse_args(child, ip, 1)  # exit(32)
            label = parse_label(ip, args[0])
            if label not in enviroment.label:
                error(ip, 52, 'Navesti "' + label + '" nenalezeno')  # exit(52)
            if len(enviroment.stack) < 2:
                error(ip, 56, 'Na datovem zasobniku musi byt alespon 2 hodnoty!')  # exit(56)
            symb2 = enviroment.stack.pop()
            symb1 = enviroment.stack.pop()
            if symb1.type != symb2.type:
                error(ip, 53, opcode + ': arg2 a arg3 museji byt stejneho typu')  # exit(53)
            if opcode == "JUMPIFEQS" and symb1.value == symb2.value:
                ip = enviroment.label.get(label)
            elif opcode == "JUMPIFNEQS" and symb1.value != symb2.value:
                ip = enviroment.label.get(label)

        else:
            if opcode != "LABEL":  # Labels are already preprocessed
                sys.stderr.write('Neznama instrukce: "' + opcode + '"\n')
                sys.exit(32)

        ip += 1
        i_count += 1

    # Write statistic data
    write_stats(statpath, stati, i_count, v_count)

    sys.exit(0)
