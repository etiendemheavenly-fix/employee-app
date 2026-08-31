package com.landmark.employee;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class EmployeeControllerTest {

    @Autowired MockMvc mvc;
    @Autowired EmployeeRepository repo;

    @BeforeEach
    void setUp() { repo.deleteAll(); }

    @Test
    void healthCheck() throws Exception {
        mvc.perform(get("/api/health"))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$.status").value("healthy"))
           .andExpect(jsonPath("$.db").value("connected"));
    }

    @Test
    void listEmployeesEmpty() throws Exception {
        mvc.perform(get("/api/employees"))
           .andExpect(status().isOk())
           .andExpect(content().json("[]"));
    }

    @Test
    void createEmployee() throws Exception {
        mvc.perform(multipart("/api/employees")
           .param("name", "Jane Doe")
           .param("email", "jane@example.com")
           .param("role", "Engineer")
           .param("department", "Engineering"))
           .andExpect(status().isCreated())
           .andExpect(jsonPath("$.id").exists())
           .andExpect(jsonPath("$.name").value("Jane Doe"));
    }

    @Test
    void createEmployeeMissingFields() throws Exception {
        mvc.perform(multipart("/api/employees")
           .param("name", "Incomplete"))
           .andExpect(status().isBadRequest());
    }

    @Test
    void createDuplicateEmail() throws Exception {
        mvc.perform(multipart("/api/employees")
           .param("name", "Bob")
           .param("email", "bob@example.com")
           .param("role", "Manager")
           .param("department", "Sales"))
           .andExpect(status().isCreated());

        mvc.perform(multipart("/api/employees")
           .param("name", "Bob2")
           .param("email", "bob@example.com")
           .param("role", "Manager")
           .param("department", "Sales"))
           .andExpect(status().isConflict());
    }

    @Test
    void getEmployeeNotFound() throws Exception {
        mvc.perform(get("/api/employees/9999"))
           .andExpect(status().isNotFound());
    }

    @Test
    void updateEmployee() throws Exception {
        Employee emp = new Employee();
        emp.setName("Charlie"); emp.setEmail("charlie@example.com");
        emp.setRole("Junior"); emp.setDepartment("Engineering");
        emp = repo.save(emp);

        mvc.perform(multipart("/api/employees/" + emp.getId())
           .param("name", "Charlie Updated")
           .param("role", "Senior")
           .with(req -> { req.setMethod("PUT"); return req; }))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$.name").value("Charlie Updated"))
           .andExpect(jsonPath("$.role").value("Senior"));
    }

    @Test
    void deleteEmployee() throws Exception {
        Employee emp = new Employee();
        emp.setName("Dave"); emp.setEmail("dave@example.com");
        emp.setRole("VP"); emp.setDepartment("Finance");
        emp = repo.save(emp);

        mvc.perform(delete("/api/employees/" + emp.getId()))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$.message").value("Employee deleted"));

        mvc.perform(get("/api/employees/" + emp.getId()))
           .andExpect(status().isNotFound());
    }

    @Test
    void deleteEmployeeNotFound() throws Exception {
        mvc.perform(delete("/api/employees/9999"))
           .andExpect(status().isNotFound());
    }
}
