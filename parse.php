<?php
/**
 * Author: Vladan Kudlac
 * Project: IPP
 * Date: 25.02.2018
 */

class Stats
{
	public $lines, $comments, $path, $opts;

	public function __construct()
	{
		$this->lines = 0;
		$this->comments = 0;
		$this->path = '';
		$this->opts = [];
	}
}

$instructions = [ // var = variable; symb = constant or variable; label = label
	"MOVE" => ['var', 'symb'],
	"CREATEFRAME" => [],
	"PUSHFRAME" => [],
	"POPFRAME" => [],
	"DEFVAR" => ['var'],
	"CALL" => ['label'],
	"RETURN" => [],
	"PUSHS" => ['symb'],
	"POPS" => ['var'],
	"ADD" => ['var', 'symb', 'symb'],
	"SUB" => ['var', 'symb', 'symb'],
	"MUL" => ['var', 'symb', 'symb'],
	"IDIV" => ['var', 'symb', 'symb'],
	"LT" => ['var', 'symb', 'symb'],
	"GT" => ['var', 'symb', 'symb'],
	"EQ" => ['var', 'symb', 'symb'],
	"AND" => ['var', 'symb', 'symb'],
	"OR" => ['var', 'symb', 'symb'],
	"NOT" => ['var', 'symb'],
	"INT2CHAR" => ['var', 'symb'],
	"STRI2INT" => ['var', 'symb', 'symb'],
	"READ" => ['var', 'type'],
	"WRITE" => ['symb'],
	"CONCAT" => ['var', 'symb', 'symb'],
	"STRLEN" => ['var', 'symb'],
	"GETCHAR" => ['var', 'symb', 'symb'],
	"SETCHAR" => ['var', 'symb', 'symb'],
	"TYPE" => ['var', 'symb'],
	"LABEL" => ['label'],
	"JUMP" => ['label'],
	"JUMPIFEQ" => ['label', 'symb', 'symb'],
	"JUMPIFNEQ" => ['label', 'symb', 'symb'],
	"DPRINT" => ['symb'],
	"BREAK" => []
];

$stats = new Stats();

// MAIN BEGIN //
parseParameters($argv, $stats);

$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'UTF-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode18');

parseHeader();
while (true) {
	$line = loadLine($stats);
	if (!parseLine($line, $instructions, $xml)) {
		break;
	}
}

$xml->endElement();
$xml->endDocument();
echo $xml->outputMemory();

if ($stats->path != '') {
	writeStats($stats);
}
// MAIN END //


// BODY BEGIN //
function parseParameters($argv, $stats)
{
	if (count($argv) > 1) {
		unset($argv[0]); // Drop script path
		$matches=[];

		foreach ($argv as $argument) {
			if ($argument == '--help' || $argument == '-h') {
				echo "Skript nacte ze standardniho vstupu zdrojovy kod v IPPcode18, zkontroluje lexikalni a syntaktickou spravnost kodu a vypise na standardni vystup XML reprezentaci programu." . PHP_EOL . PHP_EOL . "Parametry:" . PHP_EOL . "	--help  Vypise na standardni vystup napovedu skriptu." . PHP_EOL;
				exit(0);
			}
			else if (preg_match('~^(\-\-stats|\-s)=(.*)$~', $argument, $matches)) {
				$stats->path = $matches[2];
			}
			else if ($argument == '--loc' || $argument == '-l') {
				if (count($stats->opts)==0 || $stats->opts[0]!='lines') {
					$stats->opts[] = 'lines';
				}
				else exit(10);
			}
			else if ($argument == '--comments'  || $argument == '-c') {
				if (count($stats->opts)==0 || $stats->opts[0]!='comments') {
					$stats->opts[] = 'comments';
				}
				else exit(10);
			}
			else {
				exit(10);
			}
		}

		if (count($stats->opts) && !isset($stats->path)) { // Stats not enabled, unable to format output
			exit(10);
		}
	}
}

/**
 * Check first line for required header. Exit when line is invalid.
 */
function parseHeader()
{
	$line = trim(fgets(STDIN));
	if (strtolower($line) != ".ippcode18") {
		lineErr([$line], "Chyba - chybi uvodni radek '.IPPcode18'"); // exit (21)
	}
}

/**
 * Load one line from stdin.
 * @param Stats $stats
 * @return array|null Return array with tokens or null when reached EOF.
 */
function loadLine($stats)
{
	$comment = false;
	$line = [];
	$tmp = '';

	while (true) {
		$char = fgetc(STDIN);

		if ($char == "\n") { // Reached EOL
			break;
		}

		if ($char === false) { // Reached EOF, add special null token
			if ($tmp) $line[] = $tmp;
			$tmp = '';
			$line[] = false;
			break;
		}

		if (!$comment) {
			if ($char == "#") { // Reached comment, ignore everything till EOL or EOF
				$comment = true;
				$stats->comments++;
			}
			else if (ctype_space($char)) { // Whitespace - close token
				if ($tmp) $line[] = $tmp;
				$tmp = '';
			}
			else { // Anything else, add to token
				$tmp .= $char;
			}
		}
	}

	if ($tmp != '') $line[] = $tmp; // Close last token

	if (!empty($line)) {
		if (count($line) > 1 || $line[0] != "\0") $stats->lines++; // Don't count line with just EOF token.
	}

	return $line;
}

/**
 * Check if the line is valid and write then into XML document.
 * @param array $line
 * @param array $instructions
 * @param XMLWriter $xml
 * @return bool Return false when reached EOF, true in other case.
 */
function parseLine($line, $instructions, $xml)
{
	static $order = 0; // STATIC VARIABLE!!!
	$endOfFile = false;

	if (!empty($line)) {

		if (end($line) === false) { // Remove special EOF token
			$endOfFile = true;
			unset($line[sizeof($line)-1]);
			if (empty($line)) {
				return false;
			}
		}

		$opcode = $line[0] = strtoupper($line[0]);

		if (!isset($instructions[$opcode])) { // Instruction doesn't exist
			lineErr($line, "Neznámá instrukce: ".$opcode); // exit (21)
		}
		if (count($instructions[$opcode]) != count($line)-1) { // Incorrect number of operands
			lineErr($line, "Chybny pocet operandu instrukce '".$opcode."', pozadovano: ".count($instructions[$opcode]).", predano: ".(count($line)-1)); // exit(21)
		}

		$xml->startElement('instruction');
		$xml->writeAttribute('order', ++$order);
		$xml->writeAttribute('opcode', $opcode);

		for ($i=1; $i<count($line); $i++) {
			$xml->startElement('arg'.$i);
			switch ($instructions[$opcode][$i-1]) {
				case 'var':
					if (!parseVar($xml, $line[$i])) {
						lineErr($line, "Jako ".$i.". operand ocekavana promenna"); // exit(21)
					}
					break;
				case 'symb':
					if (!parseVar($xml, $line[$i]) && !parseSymb($xml, $line[$i])) {
						lineErr($line, "Jako ".$i.". operand ocekavana konstanta nebo promenna"); // exit(21)
					}
					break;
				case 'label':
					if (!parseLabel($xml, $line[$i])) {
						lineErr($line, "Jako ".$i.". operand ocekavano navesti"); // exit(21)
					}
					break;
				case 'type':
					if (!parseType($xml, $line[$i])) {
						lineErr($line, "Jako ".$i.". iperand ocekavan typ"); // exit(21)
					}
					break;
			}
			$xml->endElement();
		}
		$xml->endElement();
	}

	if ($endOfFile) {
		return false;
	}
	return true;
}

/**
 * Check string for variable format and write argument into XML on success.
 * @param XMLWriter $xml XML object
 * @param string $token String to evaluate
 * @return bool Return true if $token is valid, false when invalid
 */
function parseVar($xml, $token)
{
	if (preg_match("~^(LF|TF|GF)@[a-zA-Z_\-$&%*][\w_\-$&%*]*$~", $token)) {
		$xml->writeAttribute('type', 'var');
		$xml->text($token);
		return true;
	}
	return false;
}

/**
 * Check string for literal format and write argument into XML on success.
 * @param XMLWriter $xml XML object
 * @param string $token String to evaluate
 * @return bool Return type of literal or false when invalid
 */
function parseSymb($xml, $token)
{
	$type = null;

	if (preg_match("~^int@.*$~", $token)) {
		$type = 'int';
	}
	else if (preg_match("~^bool@(true|false)$~", $token)) {
		$type = 'bool';
	}
	else if (preg_match("~^string@([^\s#\\\\]|\\\\\d{3})*$~", $token)) {
		$type = 'string';
	}

	if ($type) {
		$xml->writeAttribute('type', $type);
		$xml->text(substr($token,strpos($token,'@')+1));
		return true;
	}

	return false;
}

/**
 * Check string for label format and write argument into XML on success.
 * @param XMLWriter $xml XML object
 * @param string $token String to evaluate
 * @return bool Return true if $token is valid, false when invalid
 */
function parseLabel($xml, $token)
{
	if (preg_match("~^[a-zA-Z_\-$&%*][\w_\-$&%*]*$~", $token)) {
		$xml->writeAttribute('type', 'label');
		$xml->text($token);
		return true;
	}
	return false;
}

/**
 * Check string for type format and write argument into XML on success.
 * @param XMLWriter $xml XML object
 * @param string $token String to evaluate
 * @return bool Return true if $token is valid, false when invalid
 */
function parseType($xml, $token)
{
	if (preg_match("~^(int|string|bool)$~", $token)) {
		$xml->writeAttribute('type', 'type');
		$xml->text($token);
		return true;
	}
	return false;
}

/**
 * Write statistic data into selected file.
 * @param Stats $stats
 */
function writeStats($stats)
{
	$data = "";
	foreach ($stats->opts as $opt) {
		$data.= $stats->$opt;
		$data.= PHP_EOL;
	}
	if (file_put_contents($stats->path, $data) === false) {
		exit(12);
	}
}

/**
 * Print error message for invalid line and exit with code 21.
 * @param array $line Tokens of invalid line
 * @param string $message Description of error
 */
function lineErr($line, $message)
{
	fwrite(STDERR, "Chyba na radku: ".implode(" ", $line).PHP_EOL);
	fwrite(STDERR, $message.PHP_EOL);
	exit(21);
}
// BODY END //
