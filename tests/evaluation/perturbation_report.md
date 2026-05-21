# Perturbation Report

- Base cases: 10
- Mutators applied: 7
- Total perturbations: 70
- Pass rate: 70%  (49/70)

## Failures

### TC_001 / truncate

- original : `Where is my order SE10234?`
- mutated  : `Where is`
- expected_intent : `order_tracking`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_002 / typo

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `I want to returnm y Nike shoes from order SE10567`
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_002 / strip_order_id

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `I want to return my Nike shoes from order`
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_002 / uppercase

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `I WANT TO RETURN MY NIKE SHOES FROM ORDER SE10567`
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_002 / whitespace

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `  I  want  to  return  my  Nike  shoes  from  order  SE10567  `
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_002 / filler

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `hey there um I want to return my Nike shoes from order SE10567 thanks!!`
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_002 / mix_language

- original : `I want to return my Nike shoes from order SE10567`
- mutated  : `I want to return my Nike shoes from order SE10567 (kya yeh sahi hai?)`
- expected_intent : `return_request`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / typo

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `When will my refund be credited? Order SE10567 returned 3 adys ago.`
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / strip_order_id

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `When will my refund be credited? Order  returned 3 days ago.`
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / uppercase

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `WHEN WILL MY REFUND BE CREDITED? ORDER SE10567 RETURNED 3 DAYS AGO.`
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / whitespace

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `  When  will  my  refund  be  credited?  Order  SE10567  returned  3  days  ago.  `
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / filler

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `hey there um When will my refund be credited? Order SE10567 returned 3 days ago. thanks!!`
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_003 / mix_language

- original : `When will my refund be credited? Order SE10567 returned 3 days ago.`
- mutated  : `When will my refund be credited? Order SE10567 returned 3 days ago. (kya yeh sahi hai?)`
- expected_intent : `refund_status`
- actual_intent   : `order_tracking`
- escalated=False approval=False clarified=False

### TC_004 / truncate

- original : `How do I claim warranty on my Sony headphones SE10234?`
- mutated  : `How do I claim war`
- expected_intent : `warranty`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / typo

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `Compare HP Pavilion vs eLnovo IdeaPad for college student`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / strip_order_id

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / uppercase

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `COMPARE HP PAVILION VS LENOVO IDEAPAD FOR COLLEGE STUDENT`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / whitespace

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `  Compare  HP  Pavilion  vs  Lenovo  IdeaPad  for  college  student  `
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / filler

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `hey there um Compare HP Pavilion vs Lenovo IdeaPad for college student thanks!!`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / truncate

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `Compare HP Pavilion`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False

### TC_006 / mix_language

- original : `Compare HP Pavilion vs Lenovo IdeaPad for college student`
- mutated  : `Compare HP Pavilion vs Lenovo IdeaPad for college student (kya yeh sahi hai?)`
- expected_intent : `product_inquiry`
- actual_intent   : `general_faq`
- escalated=False approval=False clarified=False
