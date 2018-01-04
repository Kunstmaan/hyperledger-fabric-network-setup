/*
	This script creates the signing identity from the certificate of a user.
*/


var path = require('path');
var fs = require('fs');

var jsrsa = require('jsrsasign');
var X509 = jsrsa.X509;

var Hash = require(path.join(__dirname, 'hash.js'));

var args = process.argv.slice(2);

if (args.length > 0 && typeof args[0] === 'string') {


	fs.readFile(args[0], 'utf8', function (err, data) {
		if (err) {

	    	return console.log(err);
		}

		var result = data.match(/(-----BEGIN CERTIFICATE-----)([^]+)(-----END CERTIFICATE-----)/mgi);

		if (result != null && result.length > 0) {
			var c = new X509();

		  	c.readCertPEM(result[0]);

		  	var pubKey = c.getPublicKey();

			var pointToOctet = function(key) {
				var byteLen = (key.ecparams.keylen + 7) >> 3;
				let buff = Buffer.allocUnsafe(1 + 2 * byteLen);
				buff[0] = 4; // uncompressed point (https://www.security-audit.com/files/x9-62-09-20-98.pdf, section 4.3.6)
				var xyhex = key.getPublicKeyXYHex();
				var xBuffer = Buffer.from(xyhex.x, 'hex');
				var yBuffer = Buffer.from(xyhex.y, 'hex');
				//logger.debug('ECDSA curve param X: %s', xBuffer.toString('hex'));
				//logger.debug('ECDSA curve param Y: %s', yBuffer.toString('hex'));
				xBuffer.copy(buff, 1 + byteLen - xBuffer.length);
				yBuffer.copy(buff, 1 + 2 * byteLen - yBuffer.length);
				return buff;
			};

			var buff = pointToOctet(pubKey);


			var hash = Hash.sha2_256(buff);
			console.log(hash);
		}
	});

}
