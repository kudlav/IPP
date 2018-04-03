<?php
/**
 * Author: Vladan Kudlac
 * Project: IPP
 * Date: 03.04.2018
 */


// MAIN BEGIN //
parseParameters($argv);
// MAIN END //


// BODY BEGIN //
function parseParameters($argv)
{
	if (count($argv) > 1) {
		unset($argv[0]); // Drop script path

		foreach ($argv as $argument) {
			if ($argument == '--help' || $argument == '-h') {
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
					. "  --parse-script=<file>" . PHP_EOL
					. "    soubor se skriptem parse.php, pri neuvedeni pouzije parse.php v aktualnim adresari" . PHP_EOL
					. "  --int-script=<file>" . PHP_EOL
					. "    soubor se skriptem interpret.py, pri neuvedeni pouzije interpret.py v aktualnim adresari" . PHP_EOL
				;
				exit(0);
			}
			else {
				exit(10);
			}
		}
	}
}
// BODY END //
