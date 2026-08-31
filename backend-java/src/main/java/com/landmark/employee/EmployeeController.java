package com.landmark.employee;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.*;
import java.util.Base64;

@RestController
@RequestMapping("/api")
@CrossOrigin
public class EmployeeController {

    private final EmployeeRepository repo;
    private final DataSource dataSource;

    public EmployeeController(EmployeeRepository repo, DataSource dataSource) {
        this.repo = repo;
        this.dataSource = dataSource;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        try (Connection c = dataSource.getConnection()) {
            c.createStatement().execute("SELECT 1");
            return ResponseEntity.ok(Map.of("status", "healthy", "db", "connected"));
        } catch (Exception e) {
            return ResponseEntity.status(503).body(Map.of("status", "unhealthy", "db", "disconnected"));
        }
    }

    @GetMapping("/employees")
    public List<Employee> list() {
        return repo.findAllByOrderByNameAsc();
    }

    @GetMapping("/employees/{id}")
    public ResponseEntity<Employee> get(@PathVariable Long id) {
        return repo.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/employees")
    public ResponseEntity<?> create(
            @RequestParam("name") String name,
            @RequestParam("email") String email,
            @RequestParam("role") String role,
            @RequestParam("department") String department,
            @RequestParam(value = "dob", required = false) String dob,
            @RequestParam(value = "photo", required = false) MultipartFile photo) {
        if (name == null || email == null || role == null || department == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "Missing required fields"));
        }
        if (repo.findByEmail(email).isPresent()) {
            return ResponseEntity.status(409).body(Map.of("error", "Email already exists"));
        }
        Employee emp = new Employee();
        emp.setName(name); emp.setEmail(email);
        emp.setRole(role); emp.setDepartment(department);
        emp.setDob(dob);
        if (photo != null && !photo.isEmpty()) {
            try {
                emp.setPhotoData(photo.getBytes());
                emp.setPhotoFilename(photo.getOriginalFilename());
            } catch (Exception e) {
                return ResponseEntity.status(500).body(Map.of("error", "Photo upload failed"));
            }
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(repo.save(emp));
    }

    @PutMapping("/employees/{id}")
    public ResponseEntity<?> update(
            @PathVariable Long id,
            @RequestParam(value = "name", required = false) String name,
            @RequestParam(value = "email", required = false) String email,
            @RequestParam(value = "role", required = false) String role,
            @RequestParam(value = "department", required = false) String department,
            @RequestParam(value = "dob", required = false) String dob,
            @RequestParam(value = "photo", required = false) MultipartFile photo) {
        return repo.findById(id).map(emp -> {
            if (name != null && !name.isEmpty()) emp.setName(name);
            if (email != null && !email.isEmpty()) emp.setEmail(email);
            if (role != null && !role.isEmpty()) emp.setRole(role);
            if (department != null && !department.isEmpty()) emp.setDepartment(department);
            if (dob != null && !dob.isEmpty()) emp.setDob(dob);
            if (photo != null && !photo.isEmpty()) {
                try {
                    emp.setPhotoData(photo.getBytes());
                    emp.setPhotoFilename(photo.getOriginalFilename());
                } catch (Exception e) {
                    return ResponseEntity.status(500).body(Map.of("error", "Photo upload failed"));
                }
            }
            return ResponseEntity.ok(repo.save(emp));
        }).orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/employees/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id) {
        if (!repo.existsById(id)) return ResponseEntity.notFound().build();
        repo.deleteById(id);
        return ResponseEntity.ok(Map.of("message", "Employee deleted"));
    }

    private Map<String, Object> convertToDto(Employee emp) {
        String photoUrl = null;
        if (emp.getPhotoData() != null) {
            photoUrl = "data:image/jpeg;base64," + Base64.getEncoder().encodeToString(emp.getPhotoData());
        }
        return Map.of(
            "id", emp.getId(),
            "name", emp.getName(),
            "email", emp.getEmail(),
            "role", emp.getRole(),
            "department", emp.getDepartment(),
            "dob", emp.getDob() != null ? emp.getDob() : "",
            "photo_url", photoUrl != null ? photoUrl : ""
        );
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        List<Employee> all = repo.findAll();
        Map<String, Long> departments = new HashMap<>();
        for (Employee e : all) departments.merge(e.getDepartment(), 1L, Long::sum);
        Employee latest = all.stream().max(Comparator.comparing(Employee::getId)).orElse(null);
        return Map.of(
            "total_employees", all.size(),
            "departments", departments,
            "latest_hire", latest != null ? convertToDto(latest) : null,
            "version", "2.0.0"
        );
    }
}
