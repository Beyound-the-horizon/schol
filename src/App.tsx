// import RowItem from "../src/assets/Components/Row item/rowItem";
import ScholarshipList from "../src/assets/Components/Scholarship List/scholarshipList"
import { scholarships } from "./data/scholarships";


export default function App() {
  return (
    <main>
          <ScholarshipList scholarships={scholarships} />
    </main>
  );
}


