# Project History

## Motivation

I wanted to reset chunks in Minecraft Bedrock worlds in order to regenerate newly added biomes.

## Solution

I created a small command-line tool called `chunk-reset-cli`.

Characteristics:

- CLI based
- Deletes chunks inside a rectangular area
- Around 300 lines of code
- Uses Amulet-Core as a dependency
- Does not redistribute any Amulet-Core code

Example dependency:

```toml
dependencies = [
    "amulet-core~=1.9,>=1.9.36",
]
```

## Licensing Concerns

Initially, I was concerned that publishing the project might violate the Amulet-Core license.

The LICENSE file inside Amulet-Core contains:

```
Copyright (c) 2026 Amulet-Team

All rights reserved.

A licence must be purchased to use this software.
```

This raised questions regarding whether an external tool depending on Amulet-Core could be published.

## Questions Asked to Amulet Team

I contacted Amulet Team through Discord.

Question:

> I created a small command-line utility for resetting chunks in Minecraft Bedrock worlds.
>
> It depends on Amulet-Core but does not redistribute any Amulet-Core source code.
>
> I would like to publish my source code on GitHub.
>
> Would this be permitted?

Response from gentlegiantJGC (Admin / Moderator / Amulet Developer):

> This is fine but all users of your software would need a licence to use Amulet's code

I then asked:

> Would it be acceptable for me to release my own source code under the MIT license, provided that I do not redistribute any Amulet-Core code and clearly state that users need a valid Amulet licence?

Response:

> Yeh that's fine

## Conclusion

The project itself can be released under the MIT License, provided that:

- No Amulet-Core code is redistributed.
- Amulet-Core remains an external dependency.
- Users are informed that they must possess a valid Amulet license.
