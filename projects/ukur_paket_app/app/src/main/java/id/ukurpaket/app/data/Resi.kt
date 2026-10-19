package id.ukurpaket.app.data

/**
 * What a scanned or typed tracking number must look like to be accepted.
 *
 * A shipping label carries several codes: on a real AnterAja label (marketplace order, Sameday) the long
 * Code 128 barcode next to "Nomor Pengiriman" holds the tracking number, "TSA-80745081104", while the small
 * QR codes hold other things (an order code, for one). Without this check, scanning the wrong code would tie
 * the size to a number that is not the parcel's. The pattern sits in Settings so other label formats can be
 * allowed without a new build.
 */
object Resi {
    /** "TSA-" and 8 to 14 digits, as on the AnterAja label above. */
    const val DEFAULT_PATTERN = "TSA-\\d{8,14}"
    const val EXAMPLE = "TSA-80745081104"

    /** Upper case, no spaces; a scanner or keyboard may add either. */
    fun normalize(raw: String): String = raw.trim().uppercase().replace(Regex("\\s+"), "")

    fun isValid(code: String, pattern: String = DEFAULT_PATTERN): Boolean =
        runCatching { Regex(pattern).matches(code) }.getOrDefault(false)
}
