## requirement update
students related to a certain class should be edited manually as well, due to some classes may involve some unplaned students. 

## for next step implementation 


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

- [x] if the course status has been changed especially from published to unpublished or any non-published the status, the correlate post on WooCommerce should be marked as draft as well and in the description of  Wordpress all the fields that are essential to the users should be included as well. for example vacancy, enrolment deadline, fees, dates, facility (location). dont indicate the teachers and classroom as they might be changed. and when Edit course, all the existing values of fields should be prefilled, i noticed that enrolment deadline is empty for example. please check that as well. 

- [x] when course changed from published -> draft, the woocommerce item is deleted. this is wrong, you should never delete item from woocommernce, instead, you should make it draft as well, so as published -> expired. and you dont have to change bookable status, as they should only be used when published. if draft or expired, the course should be unexisting in the option of enrolment, making it impossible to access, so the bookable is not effective (check the current code implementaion, if not like this, should be fixed.) and not all fields are prefilled when edit, e.g. deadline, and start date and end date (although they are disabled from editing, they still should show the current value)

- [x] when add class from course detail page, the class creation form should have course prefilled to avoid user mistake. and make the course select fields disabled. -- trae WIP. 

- [x] in the course detail page, there should be a enrolment public url copy button, to copy the url to clipboard and share. this enrolment url should be publicly accessible, while there is a arg to specify the course selection. this should be the same when used as `enrol now` button link when synchronise with WooCommerce.  --WIP 
  - [ ] test copy 
  - [ ] test public access with preselected course.
  - [ ] test woocommerce button link with preselected course.

- [x] enrolment should be able to added from course detail page, with a button to add enrolment. and the enrolment form should have course prefilled to avoid user mistake. and make the course select fields disabled. noted the enrolment form should be for operator of the organisatoin, able to cover all the fields. but to make it user friendly, first we need the operator to select student by search to find, if not exists, create a new student first. and in the enrolment, let the operator check if this enrolment has registration fee or not. and default with pending status, which mean after the enrolment created with pending, the email for enrolment confirmation will be sent to the contact of the enrolment, along with the right amount of fee. as there is a enrolment creation under enrolment page `/enroll/enrollments/create/`, you should refine this part as well, because the only different is course selection is prefilled or not. the rest of requirmenets are exactly the same.  -- claude code planning 

- [x] the single session class should have add class as well, to keep the consistency of interaction, but it can only create one. which means either it was created along with the course creation, or added thru the interaction in the course detail page. and the class creation form should have course prefilled to avoid user mistake. and make the course select fields disabled.

- [x] considering australia has GST, we should have Price include GST in organisational setting, so as the price shown in woocommerce product page. and in the enrolment submission confirmation email, we should indicate the price include GST or not. marked as checked by default. and check if you have any additional logic relevant to this to be added.
  - [] test GST setting in organisational setting, and course price shown in woocommerce product page.
  - [] test enrolment submission confirmation email, indicate the price include GST or not.
  - [] test course create and edit, with price include GST or not.
  - [] test enrolment creation by operator, with registration fee included in the total amount 

- [x] #bug when update course from draft to published, the woocommerce product is not created. and make the published status just above the save/create/update button, to make it more obvious.
  - [x] test course create with published status, and check woocommerce product created with right information.
  - [x] test course edit from draft to published, and check woocommerce product created with right
  - [x] test course edit from published to draft, and check woocommerce product marked as draft.
  - [] test course edit from published to expired, and check woocommerce product marked as draft.
  - [] test course edit from draft to expired, and check woocommerce product marked as draft.
  - [] test course edit from expired to published, and check woocommerce product created or updated (if this item exists) with right information.
  - [] test the mapping between the system and woocommerce product fields, are updated along with the editing of course. e.g. vacancy, enrolment deadline, fees, dates, facility (location). 
  - [] test before create a new product on woocommerce, the system always check if there is an existing product with the external_id saved in the course, if exists, update it, otherwise create a new one. there could be situation that the product is deleted on woocommerce side, but the course still exists in the system. so in this situation, when you try to publish the course, you should create a new product on woocommerce and update the external_id in the course.


- [x] http://127.0.0.1:9001/academics/courses/40/ why this course in the course list showing as published status, while in the detail page showing as expired? is there any other places having such issue? please check and fix it. and review other information accuracy as well.

- [x] in course list, only published course should show bookable or closed or fully booked status, other status don't need to show these statuses as they are no use here. thus to reduce unnecessary information load.

### class 
- [x] there should be a class entry in course list page, to show class list of all courses, with filter by course, facility, date range, teacher, classroom and active status. and the class item should have view detail action to go to class detail page. the classes could be in card style if the elements are too many to show in one line. Try leverage the current class implementation to avoid rework and potential bugs.

- [x] classroom should be under facility, which means when the facility is selected, the classroom should be filtered to show only classrooms under the selected facility. and when create / edit class, the facility should be prefilled with the course default facility. and check if other places should be aligned with this logic

### attendance 
- [x] refine the design and layout of attendance page to aligned with other page. I will list some unsatisfied status quo: 1. as current title is in gradient, which should be in solid color; 2. quick actions could have a better layout, e.g. right alinged just above the table of students. 3. remove `Mark all absent` as this is absurd


### enrolment
- [x] after submission, the email should include bank transfer information, and if new student, the registration fee (if any) should be included in the total amount. and the course should have a new enrolment added as well, with pending status. and the vacancy should not be changed until the enrolment is confirmed by operator.

- [x] The enrollment URL copied from course detail page should be identical to the public enrollment URL, with the only addition being a course ID parameter. When accessing this URL, the course selection dropdown should automatically pre-select the specified course. For example:
  - Public enrollment URL: `/enroll/public`
  - Course-specific enrollment URL: `/enroll/public?course=123`
  - Test: Access the course-specific URL and verify that the course selection dropdown pre-selects the specified course.


- [x] in the course detail, should remove `Enrol Now` button, as there should be only two ways to enrol, 1. copy the public enrolment link to this course for customers to fill, and 2. add enrolment by the operators, thru the button above the enrolment section in the course detail. and please help me test the operator adding enrolment. review the current implementation /enroll/enrollments/staff/create/39/. expected: 1. choose student first, create one if not exists; 2. remove the current adding new student modal popped in the enrolment create form, instead, new window open /students/add/ to maintain the same form for the same purpose. 

- [] enrolement should have `referred by` to be optional, a textbox for referral name. and this should also be a field in the enroled student profile

- [x] in course detail, for the course is not in published status, the enrolment button should be hidden, as the course is not bookable. but keep the enrolment list to show existing enrolments.

- [x] add enrolment in a course, should automatically add the student to existing classes of this course, if there is any. and add a new class under the course, should automatically add all existing enrolments of this course to the new class. and add a student in a class, should only affect the current class, not the whole course.
  - [] testing

- [x] the refernece ID in the enrolment submission success page, should show like the format "PAS-[courseID in 3 digits]-[enrolmentID in 3 digits]", e.g. PAS-001-023, to make it more professional and easier to identify the course and enrolment. and this should be shown in the submission confirmation email as well.
  - [] testing

- [x] enrolment cards in the course detail page should be clickable to go to the enrolment detail page, instead of just showing the information. and the enrolment detail page should have all the information of the enrolment, and able to be edited. and in the edit page, the course should be disabled to avoid mistake. and since the student could be created or extracted from the enrolment, the student profile should be a link to go to the student detail page. 

- [x] review the current email content sent upon enrolment submission, and make it more professional. and include bank transfer information, and if new student, the registration fee (if any) should be included in the total amount. and the vacancy should not be changed until the enrolment is confirmed by operator. and all the content of the email should be accurate (currently seems no duration of the course. please review all of others as well). and currently there are two emails sent out upon the submission, which the submission should be only one email sent to the contact email provided in the enrolment form, including the course information and bank transfer information. and when the enrolment is confirmed by operator, then another email should be sent to the contact email to indicate the enrolment is confirmed.
  - [] testing

- [x] why the enrolment detail page has `Original Form Data` section? is it necessary? can we remove it to avoid confusing?

- [x] the same class / course should not enrol the same student more than once. so when create enrolment, if the student already has an existing enrolment in the same course (regardless of status), then should not allow creating another enrolment for the same course. and if the student already has an existing enrolment in the same class (regardless of status), then should not allow creating another enrolment for the same class. please implement this logic and test it.

### settings 
- [ ] SMS configuration should be only visible to admin user of the organisation, so as the email configuration.
- [x] the staff user should only be able to see their profile and change password, see their upcoming classes with students, and mark attendance, and clock in and out. ref: 00-plans/staff-teacher-portal-minimal-changes.md. -- WIP 
  - [x] test staff user can only see their profile and change password, see their upcoming classes with students, and mark attendance, and clock in and out. *(91.7% complete - clock templates missing)*
  - [x] test admin user can see all settings including SMS and email configuration.
  - [x] test email and SMS configuration only visible to admin user of the organisation.
  - [x] test staff user cannot see SMS and email configuration.
  - [x] test admin user can see all staff and their details.
  - [x] test staff user can only see their own details.
  - [x] test staff user can change their own password.
  - [x] test staff user can see their upcoming classes with students.
  - [x] test staff user can mark attendance for their classes.
  - [ ] test staff user can clock in and out. *(Template missing: core/clock/clockinout.html)*

- [x] the current implementation of GST in settings is verbose, and should be simplified. as in Australia, everyone knows how GST works, it's unncesary to ask for rate and label, and show GST with too many 0 after the dot, just 10% is enough. and no test GST preview, and preview. Just a pure Price inputted with GST or not as checkbox for global configuration. this is quite like woocommerce price with GST display. 
  - [x] test GST setting in organisational setting, and course price shown in woocommerce product page.
  - [x] test enrolment submission confirmation email, indicate the price include GST or not.
  - [x] test course create and edit, with price include GST or not.
  - [ ] test enrolment creation by operator, with registration fee included in the total amount.
  - [ ] test enrolment creation by student, with registration fee included in the total amount.

- [x] make the default SMS quota as 200 per month.

### Student 
- [x] based on our enrolment form, the contact should only have one email and one phone number, either it's student or guardian, depending on the age of the student. so in the student create and edit page, we should align with this logic. currently it has email address while guardian email address, which is not right. there should be only one contact email. no matter it's for guardian or student. and the same for phone number. in the future if want to use the contact, we detect if guardian name is provided, then the contact email and phone number are guardian's, otherwise, it's student's. 
  - [x] test student create and edit page, align with enrolment form logic, only one contact email and one phone number.
  - [x] test student create and edit page, if guardian name is provided, then the contact email and phone number are guardian's, otherwise, it's student's.

- [x] in student detail page, review the code to see if all the infomration shown are accurate. e.g. attendance history.


### Staff 
- [x] why in staff detail page, there could be showing staff role is not staff in system access panel? it's confusing, especially for those who are not aware of there is django admin backend. what do you recommend? should we change the label or remove this panel? and check the information of this page is accurate or not.

- [x] staff row in staff list page, when clicked, there is a error showing Page not found (404)
Request Method:	GET
Request URL:	http://127.0.0.1:9000/accounts/staff/undefined.

Please fix it and test it.

- [x] in staff detail page, there should be a timesheet panel, to show their clock in and out history, with date range filter. and the timesheet should be exportable as csv or excel. and the timesheet should show total hours worked in the date range as well. the timesheet should have clock in and out as paired in one entry of one specific class.

#### timesheet 
- [x] in staff list page, there should be a timesheet button/link to go to timesheet page, to show all staff timesheet with date range filter. and the timesheet should be exportable as csv or excel. and the timesheet should show total hours worked in the date range as well. the timesheet should have clock in and out as paired in one entry of one specific class.
  - [ ] testing

### Facility & classroom 
- [ ] in class list there might be some class with `room 1` as classroom, while the facility has no such classroom. and when i tried to change its facility and classroom, it shows error as attached. please check if the classroom information is accurate or not. and check if other places have similar issue. please fix it and test it.