## requirement update
students related to a certain class should be edited manually as well, due to some classes may involve some unplaned students. 

## for next step implementation 
[x] in course detail page, should we change the layout of description as it is rich content with potential images and other html content? or is there any other better layout structure for the course detail page?
  - [ ] need test
- staff edit/ create, when click update, the page has no response, and not take effect. check if similar issues in other modules. 
  - [ ] need test 

- [x] class / session should have their own detail page, and able to be edited for all its elements, even they still keep the hierarchy relationship with Course. some user stories here are 1. students related to a certain class should be edited manually as well, due to some classes may involve some unplaned students; 2. teacher might be changed due to shift/leave; 3. occasionally, classroom and time may be changed as well. There might be a tricky part for the same elements between course and class/session (e.g. start time, teacher,) how should we handle the situation? should we restrict some course elements not editable once created? or should we allow changes on all, but let operator select which classes will be affected (all selected by default)? 
  - [ ] test

- [x] duration in course should be able to use hours + minutes format, with minutes in step of 10 mins select.

- [x] enrolment CRUD, with public accessible link for creating enrolment as well, making enrolment can be created by system operator as well as students/ guardians. 
  - [ ] test



- [x] 1. in course detail page, the view action in class list below is not working. when clicked, it will bring up to the top of current page instead of showing the class detail page. 2. the head of with blue background and white course title, making the contrast unclear, refine it; 3. right side panel for course actions could be removed, and put view all enrolment inside the enrolment side panel (with a view all link out?), add class can only exist in class list panel and that's enough, generate class button can be removed for now.


- [x] update staff doens't work. staff view / detail page is not working as well. and all the phone number should allow Australian phone number format, e.g. 0412 345 678. check any other places have similar issue. 

- [x] in course create / edit page, schedule information, we should show repeat pattern first. as if this is single session, then the start date and end date should be hidden, instead, show a single session date is enough. ~~and currently the duration has equal-wide hour and minute, to make them in one line, we should make them narrow so they should be shown in one line~~. and if this is a single session, the course should not allow add class action.



- [x] course should have status: draft, published, expired(? for published but current date is over the end date). and have bookable state: bookable, fully_booked (vacancy is 0 as confirmed enrolments count match vacancy?), closed. and should we add accept enrolment deadline date as one of the conditions to change bookable to closed? enrolment public page should have the status detected as well, e.g. if fully booked, or closed, show this course is no longer available. please test after you implement these.

- [x] for course edit and affect classes, in the course edit page, we should have a current class list with checkbox to let operator to check which classes should be affected by the current change. if checked, then the changes on date (e.g. course changed from every monday, to every thursday), start time, duration, teacher, facility and classroom. 

- [x] in course detail, should have a enrolment url with the current course as args, so when click this enrolment, ppl should be able to have the course default selected with the current course to continue filling. this is useful in the future for sync with woocommerce and embed the button link for enrolment. 

- [x] in the enrolment, i only expect one contact email, either it's the student, or guardian's (if student is under 18). to decide which to collect, we should put DOB above the email and phone number, and ask DOB first, if DOB filled and calculate under 18 years old, then guardian's name is a must, so the contact email and phone number are guardian's. otherwise, it's student's.

- [x] 1. course edit should not allow changing repeat pattern. as this may involve too many changes. you should disable it in edit, so as course type, and start date and end date; 2. is the checkbox: Allow Online Bookings affect enrolment form visibility? 3. what is the purpose of having Active checkbox under advance options? can we remove it if not necessary or covered by other elements?  1. disable the mentioned fields when edit to avoid overcomplicated handling; 2. make online-bookable take effect in 
  those logics. and I think to avoid confusing bookable status with this, we should make allowing online book with indicator
   is_online_bookable. do you agree? 3. i think we should remove the old is_active, and use status for the matter.

- [x] classes should be able to be deleted for management, including under a course, or in detail page? and should have confirmation mechanism? 

- [x] email with Google workspace account. but can google support SMTP to send? if yes, i would like to make the admin of the orgnaisation able to configure this in the front portal, e.g. having a email configuration item under their avatar in the top right
- [x] i want to follow the practice of email, to implement SMS sending with twilio.
  ==tested email sending.fine==

- [x] in student page, we should have a notification function, to allow send SMS/email in batch or individual (you should think harder on the UX design here). in email, you should add reply-to in case others reply the email. SMS should be no-reply (is this configured at twilio portal?). SMS and email should have monthly limitation, and configured by me in django admin (not visible for frontend) . as the contact information, or information like whether you should use guardian's name or student's name, you should review by the enrolment design.


- [x] enrolment, only show hint if student under 18. and check if you are using the only one contact email and phone number. as if student under 18, this should be their guardian, but dont need to have separate guardiant email or student email, as for phone number. otherwise when sending notification, we need to identify which contact email / sms we should send. for under 18, the only difference should be the guardian name is provided or not. and for validation, before DOB is specified, the contact information section should be disabled. do you agree such interaction?

- [x] woocommernce API prototype test. I include information in .env for woocommerce API. to test the connection, we should use a test course infomration with external product(?) to create a post? i also prefer the edit will update the content in woocommerce as well. 
  ```
  WC_CONSUMER_KEY
  WC_CONSUMER_SECRET
  WC_BASE_URL
  ```


- [x] course should support category (which is also a mapping to WooCommerce): 1. Term Courses; 2. Holiday Program; 3. Day Courses. when create / edit course, and sync course with woocommerce, this should be supported as well.

- [x] should we keep a table for monitoring the status of course synchronisation? to understand what have not been synced yet, and when changed, which post on woocommernnce should be changed (mapping)

- [x] whether we should add feature image in course create & edit? this is to map woocommerce product fields. and check if the course create and edit can both trigger sync create and changes to woocommerce product, and include button with link to enrolment url with parameter of the right course id for preselection of course from select dropdown.
  - [x] tested - Course featured_image field added successfully
  - [x] tested - WooCommerce API updated to support product images
  - [x] tested - Course creation/editing automatically syncs with WooCommerce including images
  - [x] tested - Enrollment URL with course preselection works correctly
  - [x] tested - All functionality verified: created test course (ID: 21), synced to WooCommerce (external_id: 2758)


- [x] in student page, add a batch notification feature. they can multi select student from list to send notifiaation (email or sms). to facilitate this, should we have tags for students, so they can be groupped and send by select premarked tags.

- [x] the student create and edit page, should be aligned with Enrolment, since most of the information is from enrolment. so please check both of them and align them. we can add some fields for student edited in the system, e.g. notes for teachers/operators, without showing them to frontend. and the form should have tag fields 
  
is contact email in enrolment sharing one for either student or guardian, depending on the student age? if they share the only one field, should you modify it in the student form to align it? and for the enrolment fields, since they are for courses, are they all can be included in Student information? should we distinguish what are for student and what are for course in the enrolment? especially considering the student needs to be identified by existing student or new student, because there might be a registration fee (course create/edit price should include this additional field to indicate how much for registration fee, leave blank means no fee). and what could be a good way to identify student is registered or not? a checkbox to indicate explicitly? or judge by information they provide (e.g. name + DOB)


- [x] attendance for student, in class. searchable with suggestions when add student in class. attendance should be able to be marked for single or multiple students in the list, with time specified, and able to be marked as absent or other regular attendance features. note the reasonableness of the interaction of the page and list. 

- [x] help me refine the course detail page for interaction, UI and attendance. 
- 1. make the title panel in white background instead of green, and back to classes button at the top left of the title panel. in the original place, remove delete action, and only keep edit action button. if the class is "deleted", they should be marked as inactive by uncheck the active checkbox in class edit page. 
- 2. move `mark attendance` from student panel to attendance history panel to strengthen to correlations. 
- 3. remove quick actions panel, and put view course action on the title panel next to class edit action. 
- 4. check the information accuracy in Class Statistics 
- 5. the poped action panel from 3 dots of student item, could be covered by the panels in its right. this could be a style error.
- 6 the modal of `add student` doesn't have suggestions while typing student name or email. and in case this is a new student, below the search box, provide a `cannot find any? add new student` ( you can revise the message) with a link to add a new student. 

- [x] you can see from the screenshot, the 3 dots pop up could be covered, i guess it's the hover effects, triggering other divs above the popup. and class statistics with empty string of students number. and mark attendance response error

- [x] attendance for teacher, this is standalone page as i want to teacher scan a QRcode on the site, and fill a form to clock in and out. teachers need to sign in their account first for ID, and then clock in by specifying their class and time, class could be multiple checked, class options are today's class of the facility by detecting their current location. we also need to collect their GPS to calculate (does Google GEOAPI have such feature?) if they are near the facility (so the facility address will also collect GPS, could use google GEOAPI to suggest the location when editing facility). let me know what I should provide, e.g. GEOAPI key or any others, in the .env (dotenv).

- [x] enrolment submitted, then send email as welcome email and including bank transfer information (you can generate a mockup so i can change later). and when enrolment is marked as confirmed, information emailed to contact in enrolment as well, and have activity history under student for such thing



## test item 
### course 
create: 
- course feature image synchronisation -- need to release on public
- image show in description 
- button link to enrolment 
- registration fee included in the enrolment submission confirmation letter if new student is detected. 
- vacancy update as confirmed enrolment (manually changed by operator after confirming the information and bank transfer received, not submission)
- enrolment deadline should be included as part of the description of the course when sync to woocommerce. 
- [x] #bug course list only have published, no draft. and make sure when marked as published, ask for confirmation with modal popup and indicate this will be sync to woocommerce website as well. 
- [x] if the course status has been changed especially from published to unpublished or any non-published the status, the correlate post on WooCommerce should be marked as draft as well and in the description of  Wordpress all the fields that are essential to the users should be included as well. for example vacancy, enrolment deadline, fees, dates, facility (location). dont indicate the teachers and classroom as they might be changed. and when Edit course, all the existing values of fields should be prefilled, i noticed that enrolment deadline is empty for example. please check that as well. 
- [x] when course changed from published -> draft, the woocommerce item is deleted. this is wrong, you should never delete item from woocommernce, instead, you should make it draft as well, so as published -> expired. and you dont have to change bookable status, as they should only be used when published. if draft or expired, the course should be unexisting in the option of enrolment, making it impossible to access, so the bookable is not effective (check the current code implementaion, if not like this, should be fixed.) and not all fields are prefilled when edit, e.g. deadline, and start date and end date (although they are disabled from editing, they still should show the current value)
- [ ] when add class from course detail page, the class creation form should have course prefilled to avoid user mistake. and make the course select fields disabled. -- trae WIP. 
- [ ] in the course detail page, there should be a enrolment public url copy button, to copy the url to clipboard and share. this enrolment url should be publicly accessible, while there is a arg to specify the course selection. this should be the same when used as `enrol now` button link when synchronise with WooCommerce.  
- [x] enrolment should be able to added from course detail page, with a button to add enrolment. and the enrolment form should have course prefilled to avoid user mistake. and make the course select fields disabled. noted the enrolment form should be for operator of the organisatoin, able to cover all the fields. but to make it user friendly, first we need the operator to select student by search to find, if not exists, create a new student first. and in the enrolment, let the operator check if this enrolment has registration fee or not. and default with pending status, which mean after the enrolment created with pending, the email for enrolment confirmation will be sent to the contact of the enrolment, along with the right amount of fee. as there is a enrolment creation under enrolment page `/enroll/enrollments/create/`, you should refine this part as well, because the only different is course selection is prefilled or not. the rest of requirmenets are exactly the same.  -- claude code planning 