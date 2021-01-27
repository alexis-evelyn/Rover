// Load Functions
setupMaterialUI()
overrideScrollReload()

// TODO: Add Means To Delete All Cache and Service Worker!!!

// From https://stackoverflow.com/a/17192845/6828099
function uintToString(uintArray) {
    let encodedString = String.fromCharCode.apply(null, uintArray);

    return decodeURIComponent(escape(encodedString));
}

function lookupNameFromID(twitter_account_id) {
    caches.open(accountCacheName).then(cache => {
        cache.match(twitter_account_id).then(account => {
            if (account === undefined) {
                downloadAccountInfo(twitter_account_id).then(result => {
                    console.debug("Downloaded Account Info: '" + twitter_account_id + "'")
                    updateAccountNamesOnTable(result)
                })
                return
            }

            let reader = account.body.getReader()

            reader.read().then(result => {
                console.debug("Found Account Info: '" + twitter_account_id + "'")
                updateAccountNamesOnTable(uintToString(result.value))
            })
        })
    })
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

function updateAccountNamesOnTable(accounts) {
    // TODO: Implement Proper Looping For Multi-Account Handle
    // TODO: Needs to be done for the downloading the data too
    response = $.parseJSON(accounts).accounts[0];

    $(document).ready(function () {
        $("span.account-" + response.account_id).text(response.first_name + " " + response.last_name)

        // onclick=\" window.open('https://www.twitter.com/" + item.twitter_user_id + "/statuses/" + item.id + "','_blank')\"
        //$("button.account-" + response.account_id).text("response.account_id TODO: REPLACE ME WITH FIXING ONCLICK")
    })
}

function generateTableFromTweets(tweets) {
    $(document).ready(function () {
        // Convert String To JSON
        // TODO: This particular function breaks with 22 or more tweets (based on String Size, Not Tweet Count)
        // TODO: It appears that the JSON gets chopped off in JQuery's Internal Code (Only When Embedding JSON)
        response = $.parseJSON(tweets);

        $(function() {
            let cards = ""
            $.each(response.results, function(i, item) {
                lookupNameFromID(item.twitter_user_id)  // TODO: Implement Proper Looping For Multi-Account Handle

                cards += "<div class=\"mdc-card tweet-card\">\n" +
                    "    <div class=\"mdc-card__primary-action mdc-theme--text-primary-on-dark mdc-theme--primary-bg card__content\" tabindex=\"0\">\n" +
                    "        <div>\n" +
                    "            <h2 class=\"card__title mdc-typography mdc-typography--headline6\">Tweet</h2>\n" +
                    "            <h3 class=\"card__subtitle mdc-typography mdc-typography--subtitle2\">by <span class='account-name account-" + item.twitter_user_id + "'>Loading Name For " + item.twitter_user_id + "</span> on <span class='tweet-date'>" + item.date + "</span></h3>\n" +
                    "        </div>\n" +
                    "        <div class=\"card__text mdc-typography mdc-typography--body2\">" + item.text + "</div>\n" +
                    "    </div>\n" +
                    "    <div class=\"mdc-card__actions mdc-theme--text-secondary-on-dark mdc-theme--secondary-bg card__actions\">\n" +
                    "        <div class=\"mdc-card__action-buttons\">\n" +
                    "            <button class=\"mdc-button mdc-card__action mdc-card__action--button mdc-button--raised\">  <span class=\"mdc-button__ripple\"></span> " + item.device + "</button>\n" +
                    "            <button class=\"mdc-button mdc-card__action mdc-card__action--button mdc-button--raised account-" + item.twitter_user_id + "\" onclick=\" window.open('https://www.twitter.com/" + item.twitter_user_id + "/statuses/" + item.id + "','_blank')\">  <span class=\"mdc-button__ripple\"></span> View Tweet</button>\n" +
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
    $(document).ready(function () {
        let ripple_buttons = document.querySelectorAll('.ripple-button');

        ripple_buttons.forEach(function(ripple_button) {
            mdc.ripple.MDCRipple.attachTo(ripple_button);
        });
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

    if (typeof item === "object" && item !== null) {
        return true;
    }

    return false;
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