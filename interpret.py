# coding=utf-8

import getopt
import sys
import xml.etree.ElementTree as etree
import re


class Enviroment:
    def __init__(self):
        self.gf = {}
        self.lf = None
        self.tf = None
        self.stack = []
        self.label = {}  # {string: int}
        self.call = []  # int[]


class Variable:
    def __init__(self, datatype=None, value=None):
        self.type = datatype
        self.value = value

    def __repr__(self):
        return str(self.type)+"@"+str(self.value)


class Argument:
    def __init__(self, argtype, value):
        self.type = argtype
        self.value = value


def help_print():
    # type: () -> None
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
    # type: (int, int, str) -> None
    sys.stderr.write(msg + ", instrukce " + str(order) + "\n")
    sys.exit(errno)


def parse_args(child, order, argc):
    # type: (etree.Element, int, int) -> list
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
    # type: (int, Argument) -> str
    if arg.type != "type":
        error(order, 53, 'Ocekavan argument typu "type", uveden: "' + arg.type + '"')
    if arg.value not in ["int", "string", "bool", "float"]:
        error(order, 53, 'Argument "' + arg.value + '" typu "type" nesplnuje pozadovany tvar')
    return arg.value


def parse_label(order, arg):
    # type: (int, Argument) -> str
    if arg.type != "label":
        error(order, 53, 'Ocekavan argument typu "label", uveden: "' + arg.type + '"')
    if re.fullmatch("[a-zA-Z_\-$&%*][\w_\-$&%*]*", arg.value) is None:
        error(order, 53, 'Argument "' + arg.value + '" typu "label" nesplnuje pozadovany tvar')
    return arg.value


def parse_var(order, arg):
    if arg.type != "var":
        error(order, 53, 'Ocekavan argument typu "var", uveden: "' + arg.type + '"')
    match = re.fullmatch("(LF|TF|GF)@([a-zA-Z_\-$&%*][\w_\-$&%*]*)", arg.value)
    if match is None:
        error(order, 53, 'Argument "' + arg.value + '" typu "var" nesplnuje pozadovany tvar')
    return match


def get_var(enviroment, order, match):
    if match[1] == "GF":
        return enviroment.gf.get(match[2])
    elif match[1] == "TF":
        if enviroment.tf is None:
            error(order, 55, "Docasny ramec neni definovan")  # exit(55)
        return enviroment.tf.get(match[2])
    elif match[1] == "LF":
        if enviroment.lf is None:
            error(order, 55, "Lokalni ramec neni nedefinovan")  # exit(55)
        return enviroment.lf.get(-1).get(match[2])


def get_symb(enviroment, order, arg, undefined=False):
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
            error(order, 53, 'Hodnota "' + arg.value + '" neni typu bool')  # exit(55)
    elif arg.type == "string":
        if arg.value is None:
            var.value = ""
        else:
            if re.fullmatch("([^\s#\\\\]|\\\\\d{3})+", arg.value) is None:
                error(order, 53, 'Argument "' + arg.value + '" typu "string" nesplnuje pozadovany tvar')
            var.value = arg.value
    elif arg.type == "float":
        try:
            var.value = float(arg.value)
        except (ValueError, TypeError):
            error(order, 53, 'Hodnota "' + str(arg.value) + '" neni typu float')  # exit(55)
    elif arg.type == "var":
        match = parse_var(order, arg)
        var = get_var(enviroment, order, match)
        if var is None:
            error(order, 54, 'Cteni z neexistujici promenne "' + arg.value + '"')  # exit(54)
        if var.type is None or var.value is None:
            if undefined:
                return None
            error(order, 56, 'Promenne "' + arg.value + '" nebyla dosud prirazena hodnota')  # exit(56)
    else:
        error(order, 53, 'Ocekavan argument typu int/bool/string/float nebo var, uveden: "' + arg.type + '"')
    return var


if __name__ == "__main__":
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hs:", ["help", "source="])
    except getopt.GetoptError as err:
        if err.opt != "":
            sys.stderr.write("Nespravne pouziti parametru: " + err.opt + "\n")
            help_print()
        sys.exit(10)

    filepath = ""

    for option, value in opts:
        if option in ("-h", "--help"):
            help_print()
            sys.exit(0)
        elif option in ("-s", "--source"):
            filepath = value
        else:
            sys.stderr.write("Neznamy parametr: " + option + "\n")
            help_print()
            sys.exit(10)

    if filepath == "":
        sys.stderr.write("Chyby povinny parametr: --source=<file>\n")
        help_print()
        sys.exit(10)

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
            i = enviroment.call.pop()

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
            enviroment.call.append(ip+1)
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
            var = get_var(enviroment, ip, match)
            if var is not None:
                error(ip, 59, 'Pokus o redefinovani promenne "' + match[0])  # exit(59)
            if match[1] == "GF":
                enviroment.gf[match[2]] = Variable()
            elif match[1] == "TF":
                enviroment.tf[match[2]] = Variable()
            elif match[1] == "LF":
                enviroment.tf[match[2]] = Variable()

        elif opcode == "POPS":
            args = parse_args(child, ip, 1)  # exit(32)
            match = parse_var(ip, args[0])
            var = get_var(enviroment, ip, match)
            if len(enviroment.stack) == 0:
                error(ip, 56, 'Datovy zasovnik je prazdny "' + match[2])  # exit(56)
            if var is None:
                error(ip, 54, 'Pristup k neexistujici promenne "' + match[0] + '"')  # exit(54)
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
                    print(symb.type)
                    print(symb.value)
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
            if symb1.type != "int" or symb2.type != "int":
                error(ip, 53, opcode + ': arg2 a arg3 musi byt cele cislo')  # exit(53)
            var.type = "int"
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
            if symb2.value < 0 or symb2.value > len(symb1.value):
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
            if symb2.value < 0 or symb2.value > len(symb1.value):
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
            if symb1.value < 0 or symb1.value > len(var.value):
                error(ip, 58, 'SETCHAR: pristup mimo rozsah retezce')  # exit(58)
            if len(symb2.value) > 0:
                error(ip, 58, 'SETCHAR: symb2 musi byt neprazdny rezetec')  # exit(58)
            var.value[symb1.value] = symb2.value[0]

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
                    var.value = float(inp)
                except (ValueError, TypeError):
                    var.value = 0.0

        else:
            if opcode != "LABEL":
                sys.stderr.write('Neznama instrukce: "' + opcode + '"\n')
                sys.exit(32)

        ip += 1
        i_count += 1

    sys.exit(0)
