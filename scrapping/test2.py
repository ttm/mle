from splinter import Browser

browser = Browser('firefox')
# Visit URL
url = "http://www.facebook.com"
browser.visit(url)
browser.fill('email', 'greenkobold@gmail.com')
browser.fill('pass', 'Jockey67')
# # Find and click the 'search' button
# button = browser.find_by_name('btnK')
button = browser.find_by_value('Log In')

# # # Interact with elements
button.click()
link = browser.find_by_id('')
# if browser.is_text_present('splinter.readthedocs.io'):
#     print("Yes, the official website was found!")
# else:
#     print("No, it wasn't found... We need to improve our SEO techniques")
