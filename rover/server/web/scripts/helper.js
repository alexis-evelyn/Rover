// Load Functions
setupMaterialUI()
overrideScrollReload()

// TODO: Add Means To Delete All Cache and Service Worker!!!

// const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
// const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function convertDateToLocalString(dateNum) {
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    // let temp = Date.parse("2021-01-26 13:20:46 +0000 UTC")
    let date = new Date(dateNum)

    let weekday = days[date.getDay()]
    let month = months[date.getMonth()]
    let day = date.getDate()
    let year = date.getFullYear()

    let tf_hour = date.getHours()

    let locale = 'en-US'  // undefined is a valid option

    let hour
    let meridian
    if (tf_hour > 12) {
        hour = (tf_hour - 12).toLocaleString(locale, {minimumIntegerDigits: 2, useGrouping:false})
        meridian = "PM"
    } else {
        hour = (tf_hour).toLocaleString(locale, {minimumIntegerDigits: 2, useGrouping:false})
        meridian = "AM"
    }

    let minute = (date.getMinutes()).toLocaleString(locale, {minimumIntegerDigits: 2, useGrouping:false})
    let second = (date.getSeconds()).toLocaleString(locale, {minimumIntegerDigits: 2, useGrouping:false})

    // Sunday, January 5, 2020 01:43:15 PM
    return "{}, {} {}, {} {}:{}:{} {}".format(weekday, month, day, year, hour, minute, second, meridian)
}

// Stolen From: https://stackoverflow.com/a/4974690/6828099
String.prototype.format = function () {
    let i = 0, args = arguments;

    return this.replace(/{}/g, function () {
        return typeof args[i] != 'undefined' ? args[i++] : '';
    });
};

// From https://stackoverflow.com/a/17192845/6828099
function uintToString(uintArray) {
    let encodedString = String.fromCharCode.apply(null, uintArray);

    return decodeURIComponent(escape(encodedString));
}

async function downloadAccountInfo(twitter_account_id) {
    console.debug("Looking Up Account Info For Account '" + twitter_account_id + "' !!!")

    // For Dynamic GET Requests
    let parameters = {"account": twitter_account_id}

    let contents;
    return $.ajax({
        type: 'GET',
        url: accountAPIURL,
        data: parameters,
        dataType: "text", // Forces Ajax To Process As String
        cache: false, // Keep Browser From Caching Data
        async: true, // Already In Async Function
        error: function (response) {
            console.error("Failed To Account Info For '" + twitter_account_id + "': ", response);
        },
        success: function (response) {
            // console.error(response)
            contents = response
        },
        complete: function (response) {
            // response.success is for some reason not cooperating
            console.debug('Successful: ' + response.success);
            console.debug('Response Code: ' + response.status)

            if (response.status === 200) {
                console.debug("Downloaded Account Info For '" + twitter_account_id + "'!!!");

                caches.open(accountCacheName).then(cache => {
                    // Delete The Cache, Then Re-add
                    cache.delete(twitter_account_id).then(() => {
                        const init = {"status": response.status, "statusText": response.statusText,
                            "headers": {
                                "Content-Type": "application/json",
                                "Content-Length": contents.length
                            }};

                        const results = new Response(contents, init);

                        cache.put(twitter_account_id, results);
                    });
                })
            } else {
                console.error("Could Not Download Account Info For '" + twitter_account_id + "'!!!")
                console.debug('Response Code: ' + response.status)
                console.debug('Response Text: ' + response.statusText)
            }
        }
    });
}

function generateTableFromTweets(tweets) {
    $(document).ready(function () {
        // Convert String To JSON
        // TODO: This particular function breaks with 22 or more tweets (based on String Size, Not Tweet Count)
        // TODO: It appears that the JSON gets chopped off in JQuery's Internal Code (Only When Embedding JSON)
        response = $.parseJSON(tweets);
        accounts = response.accounts

        // const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        $(function() {
            let cards = ""
            $.each(response.results, function(i, tweet) {
                account = accounts.find(account => account.account_id === tweet.twitter_user_id)
                dateTime = Date.parse(tweet.date)
                date = convertDateToLocalString(dateTime)

                cards += "<div class=\"mdc-card tweet-card\" id=\"tweet-" + tweet.id + "\">\n" +
                    "    <div class=\"mdc-card__primary-action mdc-theme--text-primary-on-dark mdc-theme--primary-bg card__content\" tabindex=\"0\">\n" +
                    "        <div>\n" +
                    "            <h2 class=\"card__title mdc-typography mdc-typography--headline6\">Tweet</h2>\n" +
                    "            <h3 class=\"card__subtitle mdc-typography mdc-typography--subtitle2\">by <span class='account-name'>" + account.first_name + " " + account.last_name + "</span> on <span class='tweet-date'>" + date + "</span></h3>\n" +
                    "        </div>\n" +
                    "        <div class=\"card__text mdc-typography mdc-typography--body2\">" + tweet.text + "</div>\n" +
                    "    </div>\n" +
                    "    <div class=\"mdc-card__actions mdc-theme--text-secondary-on-dark mdc-theme--secondary-bg card__actions\">\n" +
                    "        <div class=\"mdc-card__action-buttons\">\n" +
                    "            <button class=\"mdc-button mdc-card__action mdc-card__action--button mdc-button--raised view-tweet-internal account-" + tweet.twitter_user_id + "\" onclick=\"window.open('/tweet/" + tweet.id + "','_self')\">  <span class=\"mdc-button__ripple\"></span> Permalink</button>\n" +
                    "            <button class=\"mdc-button mdc-card__action mdc-card__action--button mdc-button--raised view-tweet-external account-" + tweet.twitter_user_id + "\" onclick=\"window.open('https://www.twitter.com/" + account.handle + "/status/" + tweet.id + "','_blank')\">  <span class=\"mdc-button__ripple\"></span> View On Twitter</button>\n" +
                    "        </div>\n" +
                    "    </div>\n" +
                    "</div>"
            });

            $('#gov-tweets').html(cards)
        });
    });
}

// Setup UI Animations and Stuff
function setupMaterialUI() {
    // Snackbar Notifications
    const MDCSnackbar = mdc.snackbar.MDCSnackbar;

    $(document).ready(function () {
        // Ripple Effect On Buttons
        let ripple_buttons = document.querySelectorAll('.ripple-button');

        ripple_buttons.forEach(function(ripple_button) {
            mdc.ripple.MDCRipple.attachTo(ripple_button);
        });

        // Cookie Notifications
        const cookiesAlert = new MDCSnackbar(document.querySelector('#cookies-alert'));

        if (getCookie("shown_cookie_prompt") == null) {
            cookiesAlert.timeoutMs = -1 // Indefinitely
            cookiesAlert.open()

            let cookieDate = new Date;
            cookieDate.setFullYear(cookieDate.getFullYear() + 2);
            document.cookie = "shown_cookie_prompt=true; expires=" + cookieDate.toUTCString();
        }
    });
}

// Stolen From: https://stackoverflow.com/a/33369954/6828099
function isJSON(item) {
    item = typeof item !== "string"
        ? JSON.stringify(item)
        : item;

    try {
        item = JSON.parse(item);
    } catch (e) {
        return false;
    }

    return typeof item === "object" && item !== null;
}

// Stolen From: https://www.w3schools.com/js/js_cookies.asp
function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');

    for(let i = 0; i <ca.length; i++) {
        let c = ca[i];

        while (c.charAt(0) === ' ') {
            c = c.substring(1);
        }

        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }

    return null;
}

function overrideScrollReload() {
    if (self.document === undefined) {
        return;
    }

    if (!/no-scroll=true/.test(window.location)) {
        return;
    }

    $(document).ready(function () {
        $("body").addClass("no-scroll");
    });
}