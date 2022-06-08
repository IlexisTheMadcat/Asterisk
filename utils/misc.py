from decimal import DivisionByZero
from typing import List


ZWSP = "​"

def fetch_array_item(list_array: List[list], x: int, y:int, one_based=True):
    """Get item from a list of lists. Simple arrays."""
    return list_array[y-1 if one_based else y][x-1 if one_based else x]

def set_array_item(list_array: List[list], x: int, y:int, new_value, one_based=True):
    """Set an item in a list of lists. Simple arrays."""
    list_array[y-1 if one_based else y][x-1 if one_based else x] = new_value
    return list_array

def calculate_xp(total, input=None):    
    return {"new_total":0, "leveled_up":True}

def divide_with_remainder(dividend, divisor) -> tuple:
    whole = int(dividend/divisor)
    remainder = dividend%divisor
    return (whole, remainder)

health_bars = {
    "starts": {
        "0": "<:BarS0:937877633432182805>",
        "1": "<:BarS1:937877839108251658>",
        "2": "<:BarS2:937877963368714290>",
        "3": "<:BarS3:937878019874365510>",
        "4": "<:BarS4:937878085544591370>",
        "5": "<:BarS5:937878155962757150>",
        "6": "<:BarS6:937878227970584661>",
        "7": "<:BarS7:937878297914785852>",
        "8": "<:BarS8:937878351165661214>",
        "9": "<:BarS9:937878451485028372>",
        "10": "<:BarS10:937878698521165824>",

        "-1": "<:BarSFull:937878738836807793>"
    },

    "middles": {
        "0": "<:Bar0:937892851742801950>",
        "1": "<:Bar1:937892882474479686>",
        "2": "<:Bar2:937892890963738657>",
        "3": "<:Bar3:937892908751794217>",
        "4": "<:Bar4:937892922911768597>",
        "5": "<:Bar5:937892935008145489>",
        "6": "<:Bar6:937892951521103893>",
        "7": "<:Bar7:937893018382512168>",
        "8": "<:Bar8:937893100112719892>",
        "9": "<:Bar9:937893111206662165>",
        "10": "<:Bar10:937893127824478248>",
        "11": "<:Bar11:937893141263036416>",

        "-1": "<:BarFull:937893193087873034>"
    },

    "ends": {
        "0": "<:BarE0:937885924967211038>",
        "1": "<:BarE1:937885962401366077>",
        "2": "<:BarE2:937886047906435072>",
        "3": "<:BarE3:937886178793893978>",
        "4": "<:BarE4:937886243746873445>",
        "5": "<:BarE5:937886318577475634>",
        "6": "<:BarE6:937886385526947891>",
        "7": "<:BarE7:937886442355556392>",
        "8": "<:BarE8:937886510462664765>",
        "9": "<:BarE9:937886566548914247>",
        "10": "<:BarE10:937886673021313035>",

        "11": "<:BarE11:937886726565818370>"
    },
}

prana_bars = {
    "starts": {
        "0": "<:BarS0:937902520028774450>",
        "1": "<:BarS1:937902635984486421>",
        "2": "<:BarS2:937902776430776360>",
        "3": "<:BarS3:937902839169183774>",
        "4": "<:BarS4:937902890247405568>",
        "5": "<:BarS5:937902941677977630>",
        "6": "<:BarS6:937903008837152768>",
        "7": "<:BarS7:937903091527843921>",
        "8": "<:BarS8:937903152781488178>",
        "9": "<:BarS9:937903288521748520>",
        "10": "<:BarS10:937903353428598925>",

        "-1": "<:BarSFull:937903413272911872>"
    },

    "middles": {
        "0": "<:Bar0:937906079654899733>",
        "1": "<:Bar1:937906153315250218>",
        "2": "<:Bar2:937906426322485308>",
        "3": "<:Bar3:937906482895282186>",
        "4": "<:Bar4:937906537060524042>",
        "5": "<:Bar5:937906596980326450>",
        "6": "<:Bar6:937906674298130462>",
        "7": "<:Bar7:937906723367309332>",
        "8": "<:Bar8:937906777595457586>",
        "9": "<:Bar9:937906832670879824>",
        "10": "<:Bar10:937906883224817685>",
        "11": "<:Bar11:937906963503800391>",

        "-1": "<:BarFull:937907019858448454>"
    },

    "ends": {
        "0": "<:BarE0:937911397424173056>",
        "1": "<:BarE1:937911467318050876>",
        "2": "<:BarE2:937911534376587295>",
        "3": "<:BarE3:937911611673411614>",
        "4": "<:BarE4:937911669642895410>",
        "5": "<:BarE5:937911730405773352>",
        "6": "<:BarE6:937911798131195955>",
        "7": "<:BarE7:937911938481008701>",
        "8": "<:BarE8:937911987361439794>",
        "9": "<:BarE9:937912040603910178>",
        "10": "<:BarE10:937912096891482192>",

        "11": "<:BarE11:937912182501441617>"
    },
}

def emoji_value_bar(current, maxi, length, emoji_bars):
    emoji_bar_part = []
    per_emoji = int(maxi/length)
    for i in range(1, length+1):
        if not current:  # grey region
            if i == 1:
                emoji_bar_part.append(emoji_bars["starts"]["0"])
            elif i == length:
                emoji_bar_part.append(emoji_bars["ends"]["0"])
            else:
                emoji_bar_part.append(emoji_bars["middles"]["0"])

            continue

        elif (current-per_emoji) > 0:  # proceed with next emoji
            current -= per_emoji
            if i == 1:
                emoji_bar_part.append(emoji_bars["starts"]["-1"])
            elif i == length:
                emoji_bar_part.append(emoji_bars["ends"]["11"])
            else:
                emoji_bar_part.append(emoji_bars["middles"]["-1"])

            continue

        elif (current-per_emoji) == 0:  # end of green region, so loop to append gray regions.
            current -= per_emoji
            if i == 1:
                emoji_bar_part.append(emoji_bars["starts"]["10"])
            elif i == length:
                emoji_bar_part.append(emoji_bars["ends"]["11"])
            else:
                emoji_bar_part.append(emoji_bars["middles"]["10"])

            continue

        elif (current-per_emoji) < 0:  # There is a remainder, which means we use part of an emoji, then loop to gray regions
            if i == 1 or i == length:  # an end or start emoji
                eleventh = per_emoji/11

                numerator = 0
                for x in range(1,12):
                    if current-eleventh >= 0:
                        current -= eleventh
                        numerator += 1
                        continue
                    elif current-eleventh < 0:
                        current = 0
                        break
                
                if i == 1:
                    emoji_bar_part.append(emoji_bars["starts"][str(numerator)])
                elif i == length:
                    emoji_bar_part.append(emoji_bars["ends"][str(numerator)])

            else:  # a middle emoji
                twelfth = per_emoji/12

                numerator = 0
                for x in range(1,13):
                    if current-twelfth >= 0:
                        current -= twelfth
                        numerator += 1
                    elif current-twelfth < 0:
                        current = 0
                        break

                emoji_bar_part.append(emoji_bars["middles"][str(numerator)])
    
    return ''.join(emoji_bar_part)