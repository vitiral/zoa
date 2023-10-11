# ZoaD: dynamically typed data encoded as ZoaB

> NOTE: this has been moved as part of
> https://github.com/civboot/civlua/tree/main/zoa/README.cxt

> Recall: ZoaB is an ultra-simple data format containing only `data` (raw bytes)
> and `array` (list of zoa values). See `zoab` in [README](../README.md)


`zoad` is dynamic types encoded in zoab. It contains compact types for most
use-cases of real systems drawing much of it's inspiration from standard JSON
and SQL data types.

A dynamic value is encoded as a zaob array of `[bEnum, ...]` (except "empty"
types which are encoded as only `bEnum` byte) where enum is a single byte of data
and `...` depends on the value of `enum` as described. The encoding of names are
determined by prefix:

* `i`: big-endian integer
* `b`: raw binary data (aka bytes)
* `u8`: utf8 encoded binary data (aka string)
* `is`: boolean (0=false, 1=true)
* `d`: embedded dynamic type (encoded as inner-array)
* `?`: either zoab data or array (userdata only)

Additionally:
* `usertype` can be used to encode compact user-defined types (typically
  specified with zoa syntax) inside the dynamic type. The iType/u8Type are
  application-defined unique integers/strings. Decoders that cannot understand a
  usertype may replace them with an `error` in some application defined
  circumstances.
* `error` is intended for errors encountered by the decoder itself to ease
  the implementation of reporting, collection and testing of such conditions.
  Any u8Type prefixed with `Z` are reserved. The following are defined. The
  remaining fields should typically contain the entire type that caused the
  error.
  * `Zenum`: unknown enum number
  * `Zempty`: a non-empty type was encoded as data (not array)
  * `Zlen`: the type's length was invalid (too short typically)
  * `Zuser`: unknown  user type
* For the various numeric types, (integer, number, duration, time, money) the
  type determines the sign of the components.
* `number` is represented as the formula `2^exp * 1.frac` (sign=frac sign)
* "zero" and "empty" types are for data compactness, since empty values are
  extremely common for many APIs.
* `date` types come in two flavors, unspecified flavor (Common Erra) and BCE
  (Before Common Erra)

```
  0  none            : <empty> (aka python None, json null)
  1  false           : <empty> (boolean)
  2  true            : <empty> (boolean)
  3  integer0        : <empty> (integer=0)
  4  number0         : <empty> (number=0)
  5  dataEmpty       : <empty> (data of len=0)
  6  utf8Empty       : <empty> (utf8 of len=0)
  7  error:          : u8Type, u8Msg, [?1, ?2, ...]
  8  user(i)         : iType,  [?1, ?2, ...]
  9  user(u8)        : u8Type, [?1, ?2, ...]
  10 list            : [d1, d2, d3, ...]
  11 map             : [dKey1, d1, dKey2, d2, ...]
  12 integer(+)      : +integer
  13 integer(-)      : -integer
  14 number(+,+)     : +iExp, +iFrac
  15 number(+,-)     : +iExp, -iFrac
  16 number(-,+)     : -iExp, +iFrac
  17 number(-,-)     : -iExp, -iFrac
  18 number(special) : 0=NaN, 1=+infinity, 2=-infinity
  19 data            : bData
  20 utf8            : u8String
  21 duration(+)     : iSeconds [, iNanoSeconds]
  22 duration(-)     : iSeconds [, iNanoSeconds]
  23 time(+)         : +iSeconds [, +iNanoSeconds] (relative to Epoch)
  24 time(-)         : -iSeconds [, -iNanoSeconds] (relative to Epoch)
  25 datetime        : iYear,    iDay (1 = January 1st), ...(+timeOfDay)
  26 datetimeBCE     : iYearBCE, iDay (1 = January 1st), ...(+timeOfDay)
  27 date            : iYear,    iDay (1 = January 1st)
  28 dateBCE         : iYearBCE, iDay (1 = January 1st)
  29 year            : iYear
  30 yearBCE         : iYearBCE
```

