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

- [] classes under a course, should be able to be deleted

- [] email with Google workspace account. but can google support SMTP to send? if yes, i would like to make the admin of the orgnaisation able to configure this in the front portal, e.g. having a email configuration item under their avatar in the top right
- [] SMS sending with twilio
- [] Clients list