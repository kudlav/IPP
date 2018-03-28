# coding=utf-8

import getopt
import sys
import xml.etree.ElementTree as etree


class Eniroment:
    def __init__(self):
        self.gf = []
        self.lf = None
        self.tf = None


class Variable:
    def __init__(self, datatype, value):
        self.datatype = datatype
        self.value = value


def print_help():
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
          "  32   lexikalni nebo syntakticka chyba")


def check_args(opcode, argc):
    if len(child) != argc:
        sys.stderr.write('Instrukce ' + opcode + ' ocekava ' + argc + ' argumentu, predano: ' + str(len(child)) + "\n")
        sys.exit(32)


if __name__ == "__main__":
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hs:", ["help", "source="])
    except getopt.GetoptError as err:
        if err.opt != "":
            sys.stderr.write("Nespravne pouziti parametru: " + err.opt + "\n")
            print_help()
        sys.exit(10)

    filepath = ""

    for option, value in opts:
        if option in ("-h", "--help"):
            print_help()
            sys.exit(0)
        elif option in ("-s", "--source"):
            filepath = value
        else:
            sys.stderr.write("Neznamy parametr: " + option + "\n")
            print_help()
            sys.exit(10)

    if filepath == "":
        sys.stderr.write("Chyby povinny parametr: --source=<file>\n")
        print_help()
        sys.exit(10)

    try:
        tree = etree.parse(filepath)
    except FileNotFoundError as err:
        sys.stderr.write('Soubor "' + filepath + '" neexistuje\n')
        sys.exit(11)
    except etree.ParseError as err:
        sys.stderr.write('Soubor "' + filepath + '" neobsahuje platny XML soubor\n' + err.msg + "\n")
        sys.exit(31)

    root = tree.getroot()
    if root.tag != "program" or root.get("language") != "IPPcode18":
        sys.stderr.write('Chybi korenovy element "program" s atributem "language=IPPcode18"\n')
        sys.exit(32)

    enviroment = Eniroment()

    # Browse instruction elements
    order = 0
    for child in root:
        if child.tag != "instruction":
            sys.stderr.write('Ocekavan element "instruction", nalezen "' + child.tag + '"\n')
            sys.exit(32)

        order += 1
        if child.get("order") != str(order):
            sys.stderr.write('Chybne poradi instrukce, ocekavano: "' + str(order) + '", uvedeno: "' + child.get("order") + '"\n')
            sys.exit(32)

        opcode = child.get("opcode").upper()
        print(opcode)  # TODO only for debug

        # PARSING INSTRUCTION #
        if opcode == "CREATEFRAME":
            check_args(opcode, 0)  # exit(32)
            enviroment.tf = []

        elif opcode == "PUSHFRAME":
            check_args(opcode, 0)  # exit(32)
            if enviroment.tf is None:
                sys.stderr.write("Docasny ramec nedefinovan, neni co vlozit na zasobnik ramcu\n")
                sys.exit(55)
            if enviroment.lf is None:
                enviroment.lf = enviroment.tf
            else:
                enviroment.lf.append(enviroment.tf)
            enviroment.tf = None

        else:
            sys.stderr.write('Neznama instrukce: "' + opcode + '"\n')
            sys.exit(32)

    sys.exit(0)