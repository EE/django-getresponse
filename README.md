A Django email backend for GetResponse.

## Usage

Use it like a standard email backend with an additional feature that allows setting `.tag_id` attribute on an `EmailMessage` instance.

The `.from_email` attribute must be present in `GETRESPONSE_ADDRESSES` as key, with FromFiledId as value (see settings below).

Result returned from sending mail is an int with extra attribute `getresponse_ids`.

## Settings

* `GETRESPONSE_API_TOKEN`
* `GETRESPONSE_ENDPOINT` — `https://api.getresponse.com/v3/` by default.
* `GETRESPONSE_ADDRESSES` - dict with addresses; ex. `{'noreply@example.com': 'Tz'}`.
