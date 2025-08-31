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


- [] update staff doens't work. staff view / detail page is not working as well. and all the phone number should allow Australian phone number format, e.g. 0412 345 678. check any other places have similar issue. 

- [] in course create / edit page, schedule information, we should show repeat pattern first. as if this is single session, then the start date and end date should be hidden, instead, show a single session date is enough. and currently the duration has equal-wide hour and minute, to make them in one line, we should make them narrow so they should be shown in one line. and if this is a single session, the course should not allow add class action.

- [] classes under a course, should be able to be deleted