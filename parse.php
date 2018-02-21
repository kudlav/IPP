<?php
/**
 * Author: Vladan Kudlac
 * Project: IPP
 * Date: 20.02.2018
 */


// MAIN BEGIN //
//parseParameters(); TODO: DEBUG ONLY
parseCode();
// MAIN END //

// RUBBISH BEGIN //
function parseParameters()
{
	$line = strtolower(fgets(STDIN));
	if (preg_match('~^(\-\-help|\-help)$~', $line)) {
		printHelp();
		exit(0);
	}

	if (!preg_match('~^(\.ippcode18)$~', $line)) {
		exit(10);
	}
}

function lexicalAnalyzer()
{
	$line = [];
	$tmp = "";

	while (($char=fgetc(STDIN)) != "\n") {

		if ($char == "#") { // Reached comment, close current token and leave this line
			if ($tmp) $line[] = $tmp;
			break;
		}

	}

	return $line;
}

function printHelp()
{
	echo "Skript nacte ze standardniho vstupu zdrojovy kod v IPPcode18, zkontroluje lexikalni a syntaktickou spravnost kodu a vypise na standardni vystup XML reprezentaci programu.".PHP_EOL
		.PHP_EOL
		."Parametry:".PHP_EOL
		."	--help  Vypise na standardni vystup napovedu skriptu.".PHP_EOL
	;
}
// RUBBISH END //
