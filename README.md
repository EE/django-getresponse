A Django email backend for GetResponse.

## Usage

Use it like a standard email backend with an additional feature that allows setting `.tag_id` attribute on an `EmailMessage` instance.

The `.from_email` attribute must be present in `GETRESPONSE_ADDRESSES` as key, with FromFiledId as value (see settings below).

Result returned from sending mail is an int with extra attribute `getresponse_ids`.

## Settings

* `GETRESPONSE_API_TOKEN`
* `GETRESPONSE_ENDPOINT` — `https://api.getresponse.com/v3/` by default.
* `GETRESPONSE_ADDRESSES` - dict with addresses; ex. `{'noreply@example.com': 'Tz'}`.

  `GETRESPONSE_ADDRESSES` is a mapping from email addr to "from_field_id" used by getresponse. To obtain "from_field_id"s based on email address query the api

      curl -H "X-Auth-Token: api-key $GETRESPONSE_API_TOKEN" 'https://api3.getresponse360.pl/v3/from-fields?query%5Bemail%5D=<email>'
  
* `GETRESPONSE_TIMEOUT` - int, optional. Passed to `requests` call.
