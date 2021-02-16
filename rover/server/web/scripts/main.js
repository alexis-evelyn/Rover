// Cache Names
const staticCacheName = 'pages-cache-v1';
const tweetCacheName = 'tweets-cache-v1';
const accountCacheName = 'accounts-cache-v1';

// Sync Events
const tweetSyncName = 'tweets-sync';

// Sync URLs
const tweetAPIURL = '/api/latest'
const accountAPIURL = '/api/accounts'

// Load Functions
registerServiceWorker();
installEruda();

function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    // TODO: Any way to verify the hash of a service worker?
    navigator.serviceWorker.register('/service-worker.js')
        .then(function(registration) {
          console.debug('Registration Successful, Scope Is:', registration.scope);
          setupBackgroundSync()
        })
        .catch(function(error) {
          console.error('Service Worker Registration Failed, Error:', error);
        });
  }
}

function setupBackgroundSync() {
    if ('serviceWorker' in navigator) {
        console.debug("Checking For Background Sync Capabilities and Registering")
        checkAndRegisterBackgroundSync().then(verifyBackgroundSyncRegistration)
    } else {
        console.error("Service Worker Missing From Navigator!!!")
    }
}

// Only Execute When DOM Is Loaded
function updateTweets() {
    downloadNewTweets().then(ajax => {
        // TODO: Populate Page Here
        console.log("Downloaded Latest Tweets!!!")

        // Populate DOM With Tweets
        populateTweets(ajax)
    })
}

// This Is A Separate Function So I Can Load Tweets To DOM From Cache Without Waiting To Download New Tweets
function populateTweets(json) {
    if (json !== undefined) {
        console.debug("Loaded JSON From Ajax Instead of Cache")
        generateTableFromTweets(json)
        return
    }

    caches.open(tweetCacheName).then(tweetsCache => {
        tweetsCache.match(tweetAPIURL).then(tweets => {
            if (tweets === undefined) {
                console.error("Failed To Find Key, '", tweetAPIURL, "', From '", tweetCacheName, "'!!!")
                return
            }

            let reader = tweets.body.getReader()

            reader.read().then(result => {
                generateTableFromTweets(uintToString(result.value))
            })
        })
    })
}

// Download Tweets (No Matter If Background Or DOM Loaded)
async function downloadNewTweets() {
    console.log("Downloading New Tweets!!!")

    // For Dynamic GET Requests
    let parameters = {}

    let last_tweet_cookie = getCookie("latest_tweet_id");
    if (last_tweet_cookie !== null) {
        // TODO: Properly Implement Handling Appending Tweets
        // parameters["tweet"] = last_tweet_cookie;
    }

    let contents;
    return $.ajax({
        type: 'GET',
        url: tweetAPIURL,
        data: parameters,
        dataType: "text", // Forces Ajax To Process As String
        cache: false, // Keep Browser From Caching Data
        async: true, // Already In Async Function
        error: function (response) {
            console.error("Failed To Fetch New Tweets: ", response);
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
                console.debug('Downloaded New Tweets!!!');

                caches.open(tweetCacheName).then(cache => {
                    // Delete The Cache, Then Re-add
                    cache.delete(tweetAPIURL).then(() => {
                        const init = {"status": response.status, "statusText": response.statusText,
                            "headers": {
                                "Content-Type": "application/json",
                                "Content-Length": contents.length
                            }};

                        const results = new Response(contents, init);

                        cache.put(tweetAPIURL, results);

                        if (isJSON(contents)) {
                            // Set Cookie To Make Retrieving New Tweets Only Easier
                            let cookieDate = new Date;
                            cookieDate.setFullYear(cookieDate.getFullYear() + 2);
                            document.cookie = "latest_tweet_id=" + JSON.parse(contents)["latest_tweet_id"] + "; expires=" + cookieDate.toUTCString();
                        } else {
                            // Clear Cookie If Not JSON
                            document.cookie = "latest_tweet_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
                        }
                    });
                })
            } else {
                console.error("Could Not Download New Tweets!!!")
                console.debug('Response Code: ' + response.status)
                console.debug('Response Text: ' + response.statusText)
            }
        }
    });
}

async function checkAndRegisterBackgroundSync() {
    let failed = false
    try {
        const status = await navigator.permissions.query({
            name: 'periodic-background-sync',
        });
    } catch(err) {
        console.debug("Failed periodic-background-sync. Most definitely not on Chrome!!!")
        failed = true
    }

    if (failed) {
        try {
            // Note: Firefox Currently Does Not Support This At All
            // https://wicg.github.io/background-sync/
            // https://wicg.github.io/background-fetch/
            // https://developer.mozilla.org/en-US/docs/Web/API/Permissions
            const status = await navigator.permissions.query({
                name: 'background-sync'
            });
        } catch (err) {
            console.debug("Failed background-sync")
        }
    }

    try {
        if (status.state === 'granted') {
            // Periodic background sync can be used.
            console.debug("Background Sync Access Granted!!!")
            await registerBackgroundSync()
        } else {
            // Periodic background sync cannot be used.
            console.warn("Background Sync Access Denied!!!")
        }
    } catch (err) {
        console.error("All Background Sync Registration Failed Horribly!!!")
    }
}

async function registerBackgroundSync() {
    const registration = await navigator.serviceWorker.ready;

    if ('periodicSync' in registration) {
        try {
            console.debug("Trying To Register Sync Handler: ", tweetSyncName)
            await registration.periodicSync.register(tweetSyncName, {
                // Once A Day Is: 24 * 60 * 60 * 1000
                // Every Minute Is: 60 * 1000
                minInterval: 60 * 1000,
            }).then(() => {
                console.debug("Registered Sync Handler: ", tweetSyncName)
            });
        } catch (error) {
            // Periodic background sync cannot be used.
            console.error("Failed To Register Sync Handler!!! Error: ", error)
        }
    }
}

async function verifyBackgroundSyncRegistration() {
    const registration = await navigator.serviceWorker.ready;

    if ('periodicSync' in registration) {
        const tags = await registration.periodicSync.getTags();

        // Only update content if sync isn't set up.
        console.debug("Tweet Sync Name: ", tweetSyncName)
        if (tags.includes(tweetSyncName)) {
            console.debug("Background Sync Registration Verified!!!")
        } else {
            console.warn("Background Sync Registration Failed!!!")
            // updateTweets()
        }
    } else {
        // If periodic background sync isn't supported, always update.
        console.warn("Background Sync Not Supported!!!")
        // updateTweets()  // TODO: Add Back When Properly Implemented Background Sync
    }
}

async function unregisterBackgroundSync() {
    const registration = await navigator.serviceWorker.ready;

    if ('periodicSync' in registration) {
        await registration.periodicSync.unregister(tweetSyncName).then(() => {
            console.debug("Unregistered Background Sync!!!")
        })
    }
}

// Mobile DevTools Console - Activate With /?eruda=true
function installEruda() {
    // If True, Running From Service Worker (Or Web Worker)
    if (self.document === undefined) {
        return;
    }

    // Dynamically Generated, So Cannot Use SRI
    let src = 'https://cdn.jsdelivr.net/npm/eruda';
    if (!/eruda=true/.test(window.location) && localStorage.getItem('active-eruda') !== 'true') {
        return;
    }

    import(src).then(() => {
        caches.open(staticCacheName)
            .then(cache => {
                cache.add(src).then(() => {
                    eruda.init();
                    console.debug("Eruda Saved To Cache!!!")
                })
            })
    });
}