<?php
/**
 * Author: Vladan Kudlac
 * Project: IPP
 * Date: 03.04.2018
 */

// MAIN BEGIN //
$config = parseParameters($argv);

$result = runTests($config);

showResult($result);
// MAIN END //


// BODY BEGIN //
/**
 * Print description and usage and return codes of this script.
 */
function helpPrint()
{
	echo "Skript slouzi pro automaticke testovani postupne aplikace parse.php a interpret.py" . PHP_EOL
		. PHP_EOL
		. "Pouziti:" . PHP_EOL
		. "./test.php [--help] [--directory=<path>] [--recursive] [--parse-script=<file>] [--int-script=<file>]" . PHP_EOL
		. "  --help" . PHP_EOL
		. "    vypise na standardni vystup napovedu skriptu" . PHP_EOL
		. "  --directory=<path>" . PHP_EOL
		. "    testy bude hledat v zadanem adresari, pri neuvedeni pouzije aktualni adresar" . PHP_EOL
		. "  --recursive" . PHP_EOL
		. "    testy bude hledat i rekurzivne v podadresarich" . PHP_EOL
		. "  --parse-script=<file>".PHP_EOL
		. "    soubor se skriptem parse.php, pri neuvedeni pouzije parse.php v aktualnim adresari" . PHP_EOL
		. "  --int-script=<file>" . PHP_EOL
		. "    soubor se skriptem interpret.py, pri neuvedeni pouzije interpret.py v aktualnim adresari" . PHP_EOL
		. "Navratove kody:" . PHP_EOL
        . "  0    ok" . PHP_EOL
        . "  10   chyba pri zpracovani argumentu" . PHP_EOL
        . "  11   chyba nacitani vstupniho souboru" . PHP_EOL
		. "  12   chyba pri otevrirani vystupniho souboru pro zapis" . PHP_EOL
	;
}


/**
 * Parse CLI arguments and return array containing configuration.
 * @param array $argv CLI arguments
 * @return array Configuration: "parser" with path to parse.php, "interpret" with path to interpret.py and array with all tests.
 */
function parseParameters($argv)
{
	$config = [
		"parser" => "parse.php",
		"interpret" => "interpret.py",
		"tests" => []
	];

	$recursive = false;
	$directory = ".";

	if (count($argv) > 1) {

		unset($argv[0]); // Drop script path

		// Check arguments
		foreach ($argv as $argument) {
			if ($argument == '--help' || $argument == '-h') {
				helpPrint();
				exit(0);
			} elseif (preg_match('~^\-\-directory=(.*)$~', $argument, $matches)) {
				$directory = $matches[1];
			} elseif ($argument == '--recursive') {
				$recursive = true;
			} elseif (preg_match('~^\-\-parse-script=(.*)$~', $argument, $matches)) {
				$config["parser"] = $matches[1];
			} elseif (preg_match('~^\-\-int-script=(.*)$~', $argument, $matches)) {
				$config["interpret"] = $matches[1];
			} else {
				fwrite(STDERR, "Neznamy parametr: " . $argument . PHP_EOL);
				helpPrint();
				exit(10);
			}
		}
	}

	// Check if parser exists
	if (!is_file($config["parser"])) {
		fwrite(STDERR, 'Soubor "' . $config["parser"] . '" neexistuje' . PHP_EOL);
		exit(11);
	}

	// Check if interpret exists
	if (!is_file($config["interpret"])) {
		fwrite(STDERR, 'Soubor "' . $config["interpret"] . '" neexistuje' . PHP_EOL);
		exit(11);
	}

	// Check if directory containg tests exists
	if (!is_dir($directory)) {
		fwrite(STDERR, 'Adresar "' . $directory . '" neexistuje, nebo z nej nelze cist' . PHP_EOL);
		exit(11);
	}

	// Find tests
	$config["tests"] = findFiles($directory, $recursive, []);

	return $config;
}


/**
 * Find all test inside specified directory.
 * @param string $directory Directory that will be searched
 * @param bool $recursive Search recusivelly or not
 * @param  $files Already found test, new test will be appended
 * @return array Tests inside specified directory
 */
function findFiles($directory, $recursive, $files)
{
	$content = scandir($directory);

	foreach ($content as $item) {
		$path = $directory . DIRECTORY_SEPARATOR;
		if (!is_dir($path . $item)) {
			$matches = [];
			if (preg_match('~^(.*)\.src$~', $item, $matches)) {
				$files[] = $path . $matches[1];
			}
		} elseif ($recursive && $item != "." && $item != "..") {
			$files = findFiles($path . $item, true, $files); // Search recursivelly deeper
		}
	}

	return $files;
}


/**
 * Run tests and return array with result.
 * @param array $config Config containing execution filepaths and tests
 * @return array Array containing results divided into two sub-arrays - "done" and "fail"
 */
function runTests($config)
{
	$result = [
		"done" => [],
		"fail" => []
	];

	// Create temporary files
	$tmpOut = tempnam(".", ".TO");
	$tmpRun = tempnam(".", ".TR");
	$tmpErr = tempnam(".", ".TE");

	// Run individual tests
	foreach ($config['tests'] as $test) {
		// Create non-existing files
		prepareFiles($test);

		// Read from .rc file
		if (($expectedStatus = file_get_contents($test . ".rc")) === FALSE) {
			fwrite(STDERR, "Chyba cteni ze souboru: " . $test . ".rc" . PHP_EOL);
			exit(11);
		}

		// Run parser, check return code
		$status = null;
		$none = [];
		exec('php5.6 "' . $config["parser"] . '" < "' . $test . '.src" > "' . $tmpOut . '" 2> "' . $tmpErr . '"', $none, $status);

		if ($status != 0) {
			$expectedStatus = trim($expectedStatus);
			if ($expectedStatus != $status) {
				$stderr = file_get_contents($tmpErr);
				$result["fail"][$test] = "Parser skončil chybou " . $status . ".<br>";
				if (($expectedStatus = file_get_contents($test . ".rc")) !== FALSE) {
					$result["fail"][$test] .= "Chybový výstup:<br><pre>" . nl2br($stderr) . "</pre>";
				}
			} else {
				$result["done"][$test] = "Parser správně skončil chybou " . $status . ".";
			}
			continue;
		}

		// Run interpret, check return code and expected/actual output using diff
		$status = null;
		$none = [];
		exec('python3.6 "' . $config["interpret"] . '" --source="' . $tmpOut . '" < "' . $test . '.in" > "' . $tmpRun . '" 2> "' . $tmpErr . '"', $none, $status);

		if ($expectedStatus != $status) {
			$result["fail"][$test] = "Interpret skončil s návratovou hodnotou " . $status . ", očekáváno: " . $expectedStatus . ".<br>";
			$stderr = file_get_contents($tmpErr);
			if (($expectedStatus = file_get_contents($test . ".rc")) !== FALSE) {
				$result["fail"][$test] .= "Chybový výstup:<br><pre>" . nl2br($stderr)."</pre>";
			}
		} else {
			if ($status == 0) {	// Diff output with .out file
				exec('diff "' . $tmpRun . '" "' . $test . '.out" > "' . $tmpOut . '"');
				if (($diff = file_get_contents($tmpOut))) {
					$result["fail"][$test] = "Interpret správně skončil s kódem " . $status . ".<br>";
					$result["fail"][$test] .= "Očekáván jiný výstup interpretu:<br><pre>" . nl2br($diff)."</pre>";
				}
				else {
					$result["done"][$test] = "Interpret správně skončil s kódem " . $status . ".<br>";
					$result["done"][$test] .= "Výstup interpretu odpovídá souboru out.";
				}
			}
			else {
				$result["done"][$test] = "Interpret správně skončil s kódem " . $status . ".<br>";
			}
		}
	}

	// Remove temporary files
	unlink($tmpOut);
	unlink($tmpRun);
	unlink($tmpErr);

	return $result;
}


/**
 * Check and create non-existing .in, .out and .rc files with default values.
 * @param string $base Test name - filename without extension
 */
function prepareFiles($base)
{
	if (!is_file($base . ".in")) {
		if (file_put_contents($base . ".in", "") === FALSE) {
			fwrite(STDERR, "Nelze vytvorit chybejici soubor s testy: " . $base . ".in" . PHP_EOL);
			exit(12);
		}
	}

	if (!is_file($base . ".out")) {
		if (file_put_contents($base . ".out", "") === FALSE) {
			fwrite(STDERR, "Nelze vytvorit chybejici soubor s testy: " . $base . ".out" . PHP_EOL);
			exit(12);
		}
	}

	if (!is_file($base . ".rc")) {
		if (file_put_contents($base . ".rc", "0") === FALSE) {
			fwrite(STDERR, "Nelze vytvorit chybejici soubor s testy: " . $base . ".rc" . PHP_EOL);
			exit(12);
		}
	}
}


/**
 * Generate HTML page for results, print it to stdout.
 * @param array $result Results gained from runTests function
 */
function showResult($result)
{
	// Get and print header of HTML
	$html = file_get_contents("report-top.html");
	if ($html !== FALSE) {
		echo $html;
	}

	// Print body containing tests
	$countOk = sizeof($result["done"]);
	$countErr = sizeof($result["fail"]);

	echo "<p><strong>Úspěšných " . $countOk . " z " . ($countOk + $countErr) . ".</strong></p>";

	echo "<h2>Neúspěšné testy (" . $countErr . ")</h2>";
	if ($countErr) {
		echo "<ul>";
		foreach ($result["fail"] as $test => $msg) {
			echo "<li><h3><span style='color:#f44336;'>&#10006;</span> " . $test . "</h3>" . $msg . "</li>";
		}
		echo "</ul>";
	}
	else echo "<p>Žádné neúšpěšné testy.</p>";

	echo "<h2>Úspěšné testy (" . $countOk . ")</h2>";
	if ($countOk) {
		echo "<ul>";
		foreach ($result["done"] as $test => $msg) {
			echo "<li><h3><span style='color:#4caf50;'>&#10004;</span> " . $test . "</h3>" . $msg . "</li>";
		}
		echo "</ul>";
	}
	else echo "<p>Žádné úšpěšné testy.</p>";

	// Get and print bottom of HTML
	$html = file_get_contents("report-bot.html");
	if ($html !== FALSE) {
		echo $html;
	}
}
// BODY END //
